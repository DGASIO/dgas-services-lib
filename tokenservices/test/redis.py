import asyncio
import os
import signal
import redis
import testing.redis

# adjust the defaul settings to allow unixsocket and requirepass settings
class RedisServer(testing.redis.RedisServer):

    def initialize(self):
        super().initialize()
        self.redis_conf = self.settings.get('redis_conf', {})
        if 'port' in self.redis_conf:
            port = self.redis_conf['port']
        elif self.settings['port'] is not None:
            port = self.settings['port']
        else:
            port = None
        if port == 0:
            self.redis_conf['unixsocket'] = os.path.join(self.base_dir, 'redis.sock')

    def dsn(self, **kwargs):
        params = super().dsn(**kwargs)
        if 'unixsocket' in self.redis_conf:
            del params['host']
            del params['port']
            params['unix_socket_path'] = self.redis_conf['unixsocket']
        if 'requirepass' in self.redis_conf:
            params['password'] = self.redis_conf['requirepass']
        return params

    def pause(self):
        """stops redis, without calling the cleanup"""
        self.terminate(signal.SIGTERM)


def requires_redis(func=None, pass_redis=None):
    """Used to ensure all database connections are returned to the pool
    before finishing the test"""

    def wrap(fn):

        async def wrapper(self, *args, **kwargs):

            redis_server = RedisServer(redis_conf={
                'requirepass': 'testing',  # use password to make sure clients support using a password
                'port': 0,  # force using unix domain socket
                'loglevel': 'warning'  # suppress unnecessary messages
            })

            self._app.config['redis'] = config = redis_server.dsn(db=1)  # use db=1 to test clients ability to switch database

            if 'unix_socket_path' in config:
                self._app.redis_connection_pool = redis.ConnectionPool(
                    connection_class=redis.connection.UnixDomainSocketConnection,
                    decode_responses=True,
                    password=config['password'] if 'password' in config else None,
                    path=config['unix_socket_path'])
            else:
                self._app.redis_connection_pool = redis.ConnectionPool(
                    decode_responses=True,
                    password=config['password'] if 'password' in config else None,
                    host=config['host'],
                    port=config['port'])

            # if the app has a `task_listener`, adjust it's config for the test
            if hasattr(self._app, 'task_listener'):
                await self._app.task_listener.stop_task_listener()
                await self._app.task_listener.start_task_listener()

            self.redis = redis.StrictRedis(connection_pool=self._app.redis_connection_pool)

            if pass_redis:
                kwargs['redis_server' if pass_redis is True else pass_redis] = redis_server

            try:
                f = fn(self, *args, **kwargs)
                if asyncio.iscoroutine(f):
                    await f
            finally:

                if hasattr(self._app, 'task_listener'):
                    await self._app.task_listener.stop_task_listener()

                redis_server.stop()

        return wrapper

    if func is not None:
        return wrap(func)
    else:
        return wrap
