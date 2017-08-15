import time
from asyncpg.handlers import BaseHandler
from tokenservices.handlers import RequestVerificationMixin
from tokenservices.test.base import AsyncHandlerTest
from tornado.escape import json_encode
from tornado.testing import gen_test
from dgasio.request import sign_request

FAUCET_PRIVATE_KEY = "0x0164f7c7399f4bb1eafeaae699ebbb12050bc6a50b2836b9ca766068a9d000c0"
FAUCET_ADDRESS = "0xde3d2d9dd52ea80f7799ef4791063a5458d13913"

TEST_PRIVATE_KEY = "0xe8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"
TEST_ADDRESS = "0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"

def generate_query_args(*, signature, address, timestamp):
    return "tokenSignature={signature}&tokenTimestamp={timestamp}&tokenIdAddress={address}".format(
        signature=signature, address=address, timestamp=timestamp)

class SimpleHandler(RequestVerificationMixin, BaseHandler):

    def get(self):

        self.verify_request()
        self.set_status(204)

    def post(self):

        self.verify_request()
        self.set_status(204)

class RequestVerificationTest(AsyncHandlerTest):

    def get_urls(self):
        return [
            (r"^/?$", SimpleHandler),
        ]

    @gen_test
    async def test_test_request_fetch_helper(self):
        """Tests the test helper for making signed requests"""

        resp = await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY)

        self.assertResponseCodeEqual(resp, 204)

        resp = await self.fetch_signed("/", signature="invalid", address="invalid", timestamp=int(time.time()))

        self.assertResponseCodeEqual(resp, 400)

    @gen_test
    async def test_query_argument_fetch(self):

        signing_key = TEST_PRIVATE_KEY
        address = TEST_ADDRESS
        timestamp = int(time.time())
        signature = sign_request(signing_key, "GET", "/", timestamp, None)

        resp = await self.fetch("/?{}".format(
            generate_query_args(signature=signature, address=address, timestamp=timestamp)))

        self.assertResponseCodeEqual(resp, 204)

    @gen_test
    async def test_invalid_signature(self):

        body = {
            "registration_id": "1234567890"
        }

        timestamp = int(time.time())
        signature = sign_request(FAUCET_PRIVATE_KEY, "POST", "/", timestamp, json_encode(body).encode('utf-8'))

        resp = await self.fetch_signed("/", method="POST", body=body,
                                       address=TEST_ADDRESS, timestamp=timestamp, signature=signature)

        self.assertEqual(resp.code, 400, resp.body)

        # make sure query string also fails
        resp = await self.fetch("/?{}".format(
            generate_query_args(signature=signature, address=TEST_ADDRESS, timestamp=timestamp)))

        self.assertEqual(resp.code, 400, resp.body)

    @gen_test
    async def test_expired_timestamp(self):

        timestamp = int(time.time() - 60)

        resp = await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY, method="POST", timestamp=timestamp)

        self.assertResponseCodeEqual(resp, 400, resp.body)
