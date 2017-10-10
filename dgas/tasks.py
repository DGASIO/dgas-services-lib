import asyncio
import aioredis
import tornado.ioloop
import urllib
import msgpack
import sys
import uuid
import traceback
import logging
from functools import partial
from tornado.platform.asyncio import to_asyncio_future

TASK_QUEUE_CHANNEL_NAME = 'task-queue'

log = logging.getLogger("task-log")

class TaskError(Exception):
    def __init__(self, exc_type_name, exc_message, formatted_traceback):
        if isinstance(exc_type_name, bytes):
            exc_type_name = exc_type_name.decode('utf-8')
        if isinstance(exc_message, bytes):
            exc_message = exc_message.decode('utf-8')
        if isinstance(formatted_traceback, bytes):
            formatted_traceback = formatted_traceback.decode('utf-8')
        self.exc_type_name = exc_type_name
        self.exc_message = exc_message
        self.formatted_traceback = formatted_traceback

    def format_exception(self, with_traceback=False):
        return "{}: {}{}".format(
            self.exc_type_name, self.exc_message,
            "\n{}".format(self.formatted_traceback) if with_traceback
            else "")

    def __repr__(self):
        return self.exc_message

class Task:
    def __init__(self, task_id, function, *args):
        self.task_id = task_id
        self._future = asyncio.Future()
        self.function = function
        self.arguments = args

    def pack(self):
        return msgpack.packb([self.task_id, 'call', self.function, *self.arguments], use_bin_type=True, encoding="utf-8")

    def cancel(self):
        self._future.cancel()
        if hasattr(self, '_calling_task'):
            self._calling_task.cancel()

    def set_result(self, result):
        if self._future.done():
            return  # TODO: ignore multiple results
        self._future.set_result(result)

    def set_exception(self, exc):
        if self._future.done():
            return  # TODO: ignore multiple results
        self._future.set_exception(exc)

    def __await__(self):
        return self._future.__await__()

class TaskHandler:

    def __init__(self, listener, task_id, **kwargs):
        self.application = self.listener = listener
        self.task_id = task_id
        self.initialize(**kwargs)

    def initialize(self, *args, **kwargs):
        pass

    async def _call_handler(self, fnname, args):
        try:
            func = getattr(self, fnname)
            r = func(*args)
            if asyncio.iscoroutine(r):
                r = await to_asyncio_future(r)
            while True:
                try:
                    await self.listener.aio_redis_connection_pool.publish(
                        self.listener.queue_name,
                        msgpack.packb([self.task_id, 'result', r], use_bin_type=True, encoding="utf-8"))
                    break
                except aioredis.errors.PoolClosedError:
                    # only send results back if the listener is still running
                    if not self.listener._shutdown_task_dispatch:
                        log.warning("'{}' result done after connection pool closed".format(fnname))
                    break
                except asyncio.CancelledError:
                    continue
                except:
                    log.exception("Error when sending task result")
                    await asyncio.sleep(0.1)
        except:
            if self.listener._shutdown_task_dispatch:
                pass
            elif not self.listener.aio_redis_connection_pool.closed:
                log.exception("call to '{}' threw exception".format(fnname))
                info = sys.exc_info()
                exc_type = "{}".format(info[0].__name__)
                msg = "{}".format(info[1])
                trace = "".join(traceback.format_exception(*info))
                await self.listener.aio_redis_connection_pool.publish(
                    self.listener.queue_name,
                    msgpack.packb([self.task_id, 'exception', exc_type, msg, trace], use_bin_type=True, encoding="utf-8"))
            else:
                log.exception("'{}' threw exception after connection pool closed".format(fnname))

_reserved_task_handler_functions = ['initialize']

class TaskListener:

    def __init__(self, handlers, application, queue=None, ioloop=None, listener_id=None):
        """
        handlers: list of TaskHandler classes
        application: a dgas.web.Application
        queue: the name of the subscribe channel to use for the tasks
        """

        if queue is None:
            queue = TASK_QUEUE_CHANNEL_NAME
        self.listener_id = listener_id

        self.application = application

        self.ioloop = ioloop or tornado.ioloop.IOLoop.current()
        self.queue_name = queue
        self._task_handlers = {}
        for handler, *optionals in handlers:
            if optionals:
                optionals = optionals[0]
            else:
                optionals = None
            self.add_task_handler(handler, optionals)
        self._tasks = {}
        self._running_tasks = {}
        self._shutdown_task_dispatch = False

    def add_task_handler(self, handler, optionals=None):
        if optionals is None:
            optionals = {}
        for fnname in dir(handler):
            if fnname.startswith('_') or fnname in _reserved_task_handler_functions:
                continue
            fn = getattr(handler, fnname)
            if not callable(fn):
                continue
            if fnname not in self._task_handlers:
                self._task_handlers[fnname] = []
            self._task_handlers[fnname].append((handler, optionals))

    # wrappers for task handlers to use mixins in the same
    # way tornado request handlers do
    @property
    def redis_connection_pool(self):
        return self.application.redis_connection_pool

    @property
    def connection_pool(self):
        return self.application.connection_pool

    @property
    def config(self):
        return self.application.config

    def _get_redis_config(self):
        # pulls the redis config from the application
        if not hasattr(self.application, 'config') or 'redis' not in self.application.config:
            raise Exception("Missing redis config")
        config = self.application.config['redis']
        if 'unix_socket_path' in config:
            address = config['unix_socket_path']
            db = int(config.get('db', 0))
            password = config.get('password', None)
        elif 'url' in config:
            p = urllib.parse.urlparse(config['url'])
            if p.scheme == 'unix':
                raise NotImplementedError()
            address = (p.hostname, p.port or 6379)
            password = p.password
            db = int(p.path[1:] or 0)
        else:
            address = (config['host'], int(config.get('port', 6379)))
            db = int(config.get('db', 0))
            password = config.get('password', None)
        return {
            'address': address, 'db': db,
            'password': password.encode('utf-8') if password else None
        }

    async def _task_dispatch_loop(self):

        while not self._shutdown_task_dispatch:
            try:
                await self._task_dispatch_loop_main()
            except:
                log.exception("Unhandled Error in task dispatch loop")
                await asyncio.sleep(0.1)

    async def _task_dispatch_loop_main(self):

        if hasattr(self, '_sub_con') and self._sub_con is not None:
            log.warning("Attempted to start 2nd task dispatch loop")
            return

        with await self.aio_redis_connection_pool as sub_con:
            self._sub_con = sub_con
            res = await self._sub_con.subscribe(self.queue_name)
            ch = res[0]
            while (await ch.wait_message()):
                message = await ch.get()
                try:
                    task_id, action, *args = msgpack.unpackb(message, encoding='utf-8')
                except (TypeError, ValueError):
                    log.exception("Invalid message: {}".format(message))
                    continue
                if action == 'call':
                    fnname, *args = args
                    if fnname in self._task_handlers:
                        for handler_class, optionals in self._task_handlers[fnname]:
                            try:
                                handler = handler_class(self, task_id, **optionals)
                                runner = asyncio.ensure_future(handler._call_handler(fnname, args))
                                self._running_tasks[task_id] = runner
                                runner.add_done_callback(partial(self._runner_done, task_id))
                            except:
                                log.exception("error calling function: {}".format(fnname))
                elif action == 'result':
                    if task_id in self._tasks:
                        f = self._tasks.pop(task_id)
                        f.set_result(args[0] if args else None)
                elif action == 'exception':
                    if task_id in self._tasks:
                        error = TaskError(*args)
                        f = self._tasks.pop(task_id)
                        f.set_exception(error)
                else:
                    log.error("Unknown message: {}".format(message))
                    continue

            self._sub_con = None

    def _runner_done(self, task_id, runner):
        self._running_tasks.pop(task_id)

    def start_task_listener(self):
        return asyncio.ensure_future(self._start())

    def stop_task_listener(self, *, soft=False):
        return asyncio.ensure_future(self._shutdown(soft=soft))

    async def _start(self):
        self._shutdown_task_dispatch = False
        try:
            if not hasattr(self, 'aio_redis_connection_pool') or self.aio_redis_connection_pool.closed:
                self.aio_redis_connection_pool = await aioredis.create_redis_pool(**self._get_redis_config())
            if not hasattr(self, '_disp_task') or self._disp_task.done():
                self._disp_task = asyncio.ensure_future(self._task_dispatch_loop())
        except:
            log.exception("failed to start")

    async def _shutdown(self, *, soft=False):
        self._shutdown_task_dispatch = True
        for task_id, runner in list(self._running_tasks.items()):
            if not soft and not runner.done():
                print('cancelling', task_id)
                runner.cancel()
            await runner
        if hasattr(self, '_sub_con') and self._sub_con is not None:
            self._sub_con.close()
            await self._sub_con.wait_closed()
        if hasattr(self, '_disp_task'):
            try:
                await self._disp_task
            except:
                log.exception("exception when waiting for dispatch loop close")
        if hasattr(self, 'aio_redis_connection_pool'):
            self.aio_redis_connection_pool.close()
            await self.aio_redis_connection_pool.wait_closed()

    async def _publish_task(self, task):
        """publishes the task to the redis channel"""
        try:
            await self.aio_redis_connection_pool.publish(
                self.queue_name,
                task.pack())
        except aioredis.errors.PoolClosedError:
            # ignoring pool closed errors
            pass

    def _call_task(self, task):
        """used to prevent the creation of a coroutine before the task actually gets called"""
        return asyncio.ensure_future(self._publish_task(task))

    def call_task(self, function, *args, delay=None):
        task_id = uuid.uuid4().hex
        task = self._tasks[task_id] = Task(task_id, function, *args)
        loop = asyncio.get_event_loop()
        fn = partial(self._call_task, task)
        if delay:
            task._calling_task = loop.call_later(delay, fn)
        else:
            task._calling_task = loop.call_soon(fn)
        return task

class TaskDispatcher:

    def __init__(self, task_listener):
        self._task_listener = task_listener

    def __getattr__(self, function):
        return partial(self._task_listener.call_task, function)
