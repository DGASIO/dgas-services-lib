import asyncio
from tornado.testing import gen_test
from tokenservices.test.redis import requires_redis
from tokenservices.test.database import requires_database
from tokenservices.test.tasks import requires_task_listener
from tornado.ioloop import IOLoop

from tokenservices.database import DatabaseMixin

from tokenservices.tasks import TaskHandler, TaskError
from .base import AsyncHandlerTest

class TestTaskHandler(TaskHandler):

    def hello(self, name):
        return "hello, {}".format(name)

    def throws_exception(self, name):
        name = blah  # noqa: on purpose to make sure exception is thrown by task handlers

    async def async_fn(self, val):
        await self.application.test_queue.put(val)
        return True

class TestTaskListener(AsyncHandlerTest):

    def get_urls(self):
        return []

    @gen_test
    @requires_redis
    @requires_task_listener
    async def test_call_handler_method(self, task_listener):
        task_listener.add_task_handler(TestTaskHandler)

        welcome = await self._app.task_listener.call_task("hello", "world")
        self.assertEqual(welcome, "hello, world")

    @gen_test
    @requires_redis
    @requires_task_listener
    async def test_call_bad_handler(self, task_listener):
        task_listener.add_task_handler(TestTaskHandler)
        with self.assertRaises(TaskError):
            await self._app.task_listener.call_task("throws_exception", "world")

    @gen_test
    @requires_redis
    @requires_task_listener
    async def test_call_async_handler(self, task_listener):
        task_listener.add_task_handler(TestTaskHandler)
        task_listener.test_queue = asyncio.Queue()
        val = 10
        res = await self._app.task_listener.call_task("async_fn", val)
        # async_fn returns True
        self.assertTrue(res)
        val2 = await task_listener.test_queue.get()
        self.assertEqual(val, val2)

    @gen_test
    @requires_redis
    @requires_task_listener
    async def test_call_with_ioloop_add_callback(self, task_listener):
        task_listener.add_task_handler(TestTaskHandler)
        task_listener.test_queue = asyncio.Queue()
        val = 11
        IOLoop.current().add_callback(self._app.task_listener.call_task, "async_fn", val)
        val2 = await task_listener.test_queue.get()
        self.assertEqual(val, val2)

    @gen_test
    @requires_database
    @requires_redis
    @requires_task_listener
    async def test_database_mixin_on_task_handler(self, task_listener):

        async with self.pool.acquire() as con:
            await con.execute("CREATE TABLE test (test_id SERIAL PRIMARY KEY, value VARCHAR)")

        val = "123"

        class TestDBTaskHandler(DatabaseMixin, TaskHandler):

            async def add_to_database(self, value):
                async with self.db:
                    await self.db.execute("INSERT INTO test (value) VALUES ($1)", value)
                    await self.db.commit()

        task_listener.add_task_handler(TestDBTaskHandler)

        await self._app.task_listener.call_task("add_to_database", val)
        async with self.pool.acquire() as con:
            row = await con.fetch("SELECT * FROM test")

        self.assertEqual(len(row), 1)
        self.assertEqual(row[0]['value'], val)
