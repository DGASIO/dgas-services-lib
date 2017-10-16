from dgas.test.base import AsyncHandlerTest
from dgas.test.redis import requires_redis

from dgas.handlers import BaseHandler
from dgas.redis import RedisMixin
from tornado.testing import gen_test

class Handler(RedisMixin, BaseHandler):

    async def get(self):

        key = self.get_query_argument('key')
        value = self.get_query_argument('value')

        await self.redis.set(key, value)
        self.set_status(204)

class RedisTest(AsyncHandlerTest):

    def get_urls(self):
        return [(r'^/$', Handler)]

    @gen_test
    @requires_redis(pass_redis=True)
    async def test_redis_connection(self, *, redis_server):

        await self.fetch('/?key=TESTKEY&value=1')
        self.assertEqual(await self.redis.get("TESTKEY"), b'1')

        # test pause and restart
        redis_server.pause()

        # make sure the pause actually stopped the service
        resp = await self.fetch('/?key=TESTKEY&value=2')
        self.assertEqual(resp.code, 500)

        redis_server.start()

        await self.fetch('/?key=TESTKEY&value=3')
        self.assertEqual(await self.redis.get("TESTKEY"), b'3')
