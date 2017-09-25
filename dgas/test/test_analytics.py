import asyncio
import base64
import json
import tornado.web

from tornado.testing import gen_test
from .base import AsyncHandlerTest
from dgas.handlers import RequestVerificationMixin, BaseHandler
from dgas import analytics

MIXPANEL_TOKEN = "12345"

TEST_ADDRESS = "0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"
TEST_PRIVATE_KEY = "0xe8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"
TEST_ADDRESS_DIGEST = "8a024bc928c7bc8a9a4aef084676283f29d4d939cd7521cdacbb7dee04f6e625"

class MockMixpanelHandler(tornado.web.RequestHandler):

    def initialize(self, *, method):

        self.mpmethod = method

    def process(self):
        data = self.get_argument('data')
        data = json.loads(base64.b64decode(data).decode('utf-8'))
        if self.mpmethod == 'track':
            if not isinstance(data, list):
                data = [data]
            for event in data:
                if 'properties' not in event or 'token' not in event['properties'] or event['properties']['token'] != MIXPANEL_TOKEN:
                    raise tornado.web.HTTPError(400)
                self.application.test_request_queue.put_nowait((self.mpmethod, event))
        self.write({'status': 1})

    def post(self):
        return self.process()

    def get(self):
        return self.process()

class SendEventHandler(analytics.AnalyticsMixin, RequestVerificationMixin, BaseHandler):

    def get(self):
        if self.is_request_signed():
            dgas_id = self.verify_request()
        else:
            dgas_id = None
        self.track(dgas_id, "Event", {"property": "property"},
                   add_user_agent=not bool(self.get_query_argument("no_user_agent", None)))
        self.set_status(204)

class AnalyticsTest(AsyncHandlerTest):

    def setUp(self):
        super().setUp(extraconf={'mixpanel': {'token': MIXPANEL_TOKEN}})
        self._app.mixpanel_consumer._endpoints = {
            'events': self.get_url('/mp/track'),
            'people': self.get_url('/mp/engage'),
            'imports': self.get_url('/mp/import'),
        }

    def tearDown(self):
        self._app.mixpanel_consumer.shutdown()
        super().tearDown()

    def get_urls(self):
        return [
            ("^/mp/track/?$", MockMixpanelHandler, {'method': 'track'}),
            ("^/mp/engage/?$", MockMixpanelHandler, {'method': 'engage'}),
            ("^/mp/import/?$", MockMixpanelHandler, {'method': 'import'}),
            ("^/?$", SendEventHandler)
        ]

    def get_app(self):
        app = super().get_app()
        app.test_request_queue = asyncio.Queue()
        return app

    def test_encode_id(self):
        digest = analytics.encode_id(TEST_ADDRESS)
        self.assertEqual(TEST_ADDRESS_DIGEST, digest)

    @gen_test
    async def test_track(self):
        result = await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY)
        self.assertEqual(result.code, 204)
        endpoint, event = await self._app.test_request_queue.get()
        self.assertEqual(endpoint, 'track')
        self.assertEqual(event['properties']['distinct_id'], TEST_ADDRESS_DIGEST)

    @gen_test(timeout=10)
    async def test_track_multiple(self):
        # start analytics
        await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY)
        await self._app.test_request_queue.get()
        # send 5 in a row
        for _ in range(5):
            await self.fetch_signed("/", signing_key=TEST_PRIVATE_KEY)
        # make sure requests haven't happened straight away for these
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(self._app.test_request_queue.get(), 1)
        # wait for them all to come in
        for i in range(5):
            await self._app.test_request_queue.get()

    @gen_test
    async def test_track_anonymous(self):
        result = await self.fetch("/")
        self.assertEqual(result.code, 204)
        endpoint, event = await self._app.test_request_queue.get()
        self.assertEqual(endpoint, 'track')
        self.assertEqual(event['properties']['distinct_id'], None)

class MockAnalyticsTest(AsyncHandlerTest):

    def get_urls(self):
        return [
            ("^/?$", SendEventHandler)
        ]

    @gen_test
    async def test_mock_track(self):
        result = await self.fetch("/")
        self.assertEqual(result.code, 204)
        distinct_id, event_name, data, _ = await self.next_tracking_event()
        self.assertEqual(distinct_id, None)
        self.assertIsNotNone(data)
        self.assertIn("User-Agent", data)

        result = await self.fetch("/?no_user_agent=1")
        distinct_id, event_name, data, _ = await self.next_tracking_event()
        self.assertEqual(distinct_id, None)
        self.assertIsNotNone(data)
        self.assertNotIn("User-Agent", data)
