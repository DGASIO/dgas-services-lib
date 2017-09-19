from dgas.handlers import BaseHandler, RequestVerificationMixin
from tornado.escape import json_encode
from tornado.testing import gen_test
from dgas.request import sign_request

from .base import AsyncHandlerTest

TEST_PRIVATE_KEY = "0xe8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"
TEST_ADDRESS = "0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"

class SimpleHandler(RequestVerificationMixin, BaseHandler):

    def get(self):

        self.verify_request()
        self.set_status(204)

class EnforceHttpsTest(AsyncHandlerTest):

    def setUp(self):
        super().setUp(extraconf={'general': {'enforce_https': 'redirect'}})

    def get_urls(self):
        return [
            (r"^/?$", SimpleHandler),
        ]

    @gen_test
    async def test_https_redirect(self):
        """Tests the test helper for making signed requests"""

        resp = await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY, follow_redirects=False)

        self.assertResponseCodeEqual(resp, 301)
        self.assertTrue(resp.headers['Location'].startswith('https://'))

    @gen_test
    async def test_x_proto_https_redirect(self):
        """Tests the test helper for making signed requests"""

        resp = await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY, follow_redirects=False,
                                       headers={'X-Forwarded-Proto': 'https'})

        self.assertResponseCodeEqual(resp, 204)

        resp = await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY, follow_redirects=False,
                                       headers={'X-Forwarded-Proto': 'http'})

        self.assertResponseCodeEqual(resp, 301)


class EnforceHttpsRejectTest(AsyncHandlerTest):

    def setUp(self):
        super().setUp(extraconf={'general': {'enforce_https': 'reject'}})

    def get_urls(self):
        return [
            (r"^/?$", SimpleHandler),
        ]

    @gen_test
    async def test_https_reject(self):
        """Tests the test helper for making signed requests"""

        resp = await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY, follow_redirects=False)

        self.assertResponseCodeEqual(resp, 404)
