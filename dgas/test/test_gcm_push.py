import os
from tornado.testing import AsyncTestCase, gen_test
from dgas.push import GCMHttpPushClient
import unittest

class GCMServerKeyTest(AsyncTestCase):
    """Tests that the given server key is valid
    only runs if the environment variable SERVER_KEY is set
    """

    @gen_test
    async def test_gcm_server_key(self):

        if 'SERVER_KEY' not in os.environ:
            raise unittest.SkipTest()

        client = GCMHttpPushClient(os.environ['SERVER_KEY'])

        resp = await client.send_impl({"registration_ids": ["ABC"]})

        self.assertEqual(resp.code, 200, resp.body)
