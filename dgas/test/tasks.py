import asyncio
from dgas.tasks import TaskListener

def requires_task_listener(func=None):
    """Used to ensure all database connections are returned to the pool
    before finishing the test"""

    def wrap(fn):

        async def wrapper(self, *args, **kwargs):

            if 'redis' not in self._app.config:
                raise Exception("Missing redis config from setup")

            self._app.task_listener = TaskListener([], self._app)

            kwargs['task_listener'] = self._app.task_listener

            await self._app.task_listener.start_task_listener()

            try:
                f = fn(self, *args, **kwargs)
                if asyncio.iscoroutine(f):
                    await f
            finally:
                await self._app.task_listener.stop_task_listener(soft=True)

        return wrapper

    if func is not None:
        return wrap(func)
    else:
        return wrap
