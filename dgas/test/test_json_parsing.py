from .base import AsyncHandlerTest

from dgas.handlers import BaseHandler
from tornado.testing import gen_test

class Handler(BaseHandler):

    def post(self):

        self.get_json_argument('hello')
        self.set_status(204)

class RedisTest(AsyncHandlerTest):

    def get_urls(self):
        return [(r'^/$', Handler)]

    @gen_test
    async def test_json_mixin(self):

        # check get_json_argument
        resp = await self.fetch('/', method="POST", body={"hello": "world"})
        self.assertEqual(resp.code, 204)

        # check raise error when key missing
        resp = await self.fetch('/', method="POST", body={"blah": "blah"})
        self.assertEqual(resp.code, 400)

        # check character encoding in header works fine
        resp = await self.fetch('/', method="POST", body={"hello": "world"}, headers={"Content-Type": "application/json; charset=UTF-8"})
        self.assertEqual(resp.code, 204)

        # check bad character encoding value in header doesn't cause catastrophic errors
        resp = await self.fetch('/', method="POST", body={"hello": "world"}, headers={"Content-Type": "application/json; charset=fuckyou"})
        self.assertEqual(resp.code, 400)

        # check bad character encoding doesn't cause catastrophic errors
        resp = await self.fetch('/', method="POST",
                                body=b'{"key": "\xe4\xb8\x8d\xe6\xad\xa3\xe3\x81\xaa\xe3\x82\xa8\xe3\x83\xb3\xe3\x82\xb3\xe3\x83\xbc\xe3\x83\x87\xe3\x82\xa3\xe3\x83\xb3\xe3\x82\xb0"}',
                                headers={"Content-Type": "application/json; charset=ascii"})
        self.assertEqual(resp.code, 400)

        # check bad json data doesn't cause catastrophic errors
        resp = await self.fetch('/', method="POST",
                                body=b'\xe6\x82\xaa\xe3\x81\x84json\xe3\x83\x87\xe3\x83\xbc\xe3\x82\xbf',
                                headers={"Content-Type": "application/json; charset=utf-8"})
        self.assertEqual(resp.code, 400)
