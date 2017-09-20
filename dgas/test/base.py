import asyncio
import configparser
import logging
import tornado.escape
import tornado.httputil
import tornado.websocket
import tornado.ioloop
import tornado.testing
import time
import warnings

from tornado.platform.asyncio import to_asyncio_future, AsyncIOLoop

from dgas.jsonrpc.errors import JsonRPCError
from dgas.ethereum.utils import private_key_to_address
from dgas.web import Application

from dgas.request import sign_request

from dgas.handlers import TOSHI_TIMESTAMP_HEADER, TOSHI_SIGNATURE_HEADER, TOSHI_ID_ADDRESS_HEADER

from dgas.test.analytics import MockMixpanel

logging.basicConfig()

class DgasWebSocketJsonRPCClient:

    def __init__(self, url, *, signing_key):

        if url.startswith('http://'):
            url = url.replace('http://', 'ws://')
        elif url.startswith('https://'):
            url = url.replace('https://', 'wss://')
        elif not (url.startswith('ws://') or url.startswith('wss://')):
            raise TypeError("url must begin with ws://")

        self.url = url
        self.signing_key = signing_key
        self.id = 1

        self.calls = {}
        self.subscription_message_queue = asyncio.Queue()

    async def connect(self):

        # find out if there's a path prefix added by get_url
        path = "/{}".format(self.url.split('/', 3)[-1])

        address = private_key_to_address(self.signing_key)
        timestamp = int(time.time())
        signature = sign_request(self.signing_key, "GET", path, timestamp, None)

        request = tornado.httpclient.HTTPRequest(self.url, headers={
            TOSHI_ID_ADDRESS_HEADER: address,
            TOSHI_SIGNATURE_HEADER: signature,
            TOSHI_TIMESTAMP_HEADER: str(timestamp)
        })

        self.con = await tornado.websocket.websocket_connect(request)
        return self.con

    async def handle_calls(self, call_id, future):
        if call_id in self.calls:
            raise Exception("Already waiting for a response to call with id: {}".format(call_id))
        loop_running = bool(self.calls)
        self.calls[call_id] = future

        # if there are already things in this means
        # we already have a process running and we
        # don't need to start the loop again
        if loop_running:
            return

        while self.calls:
            result = await self._read()
            if 'id' not in result:
                self.subscription_message_queue.put_nowait(result)
                continue
            fut = self.calls.pop(result['id'], None)
            if fut:
                fut.set_result(result)

    async def call(self, method, params=None, notification=False):

        msg = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params:
            msg['params'] = params
        if not notification:
            msg['id'] = self.id
            self.id += 1
        self.con.write_message(tornado.escape.json_encode(msg))

        if notification:
            return

        future = asyncio.Future()
        tornado.ioloop.IOLoop.current().add_callback(self.handle_calls, msg['id'], future)

        result = await future

        if 'error' in result:
            raise JsonRPCError(msg['id'], result['error']['code'], result['error']['message'], result['error']['data'] if 'data' in result['error'] else None)
        if 'result' not in result:
            raise JsonRPCError(msg['id'], -1, "missing result field from jsonrpc response: {}".format(result), None)
        return result['result']

    async def read(self, *, timeout=None):
        if not self.subscription_message_queue.empty():
            return self.subscription_message_queue.get_nowait()
        if self.calls:
            return await asyncio.wait_for(self.subscription_message_queue.get(), timeout)
        else:
            return await self._read(timeout=timeout)

    async def _read(self, *, timeout=None):

        f = self.con.read_message()
        if timeout:
            try:
                result = await asyncio.wait_for(to_asyncio_future(f), timeout)
            except asyncio.TimeoutError as e:
                # reset the connection's read state
                self.con.read_future = None
                return None
        else:
            result = await f

        if result:
            result = tornado.escape.json_decode(result)
        return result

class AsyncHandlerTest(tornado.testing.AsyncHTTPTestCase):

    APPLICATION_CLASS = Application

    @property
    def log(self):
        return logging.getLogger(self.__class__.__name__)

    def get_new_ioloop(self):
        io_loop = AsyncIOLoop()
        asyncio.set_event_loop(io_loop.asyncio_loop)
        return io_loop

    def setUp(self, extraconf=None):
        # TODO: re-enable this and figure out if any of the warnings matter
        warnings.simplefilter("ignore")
        self._config = configparser.ConfigParser()
        conf = {
            'general': {'debug': True},
        }
        if extraconf:
            conf.update(extraconf)
        self._config.read_dict(conf)
        super(AsyncHandlerTest, self).setUp()

    def get_app(self):
        app = self.APPLICATION_CLASS(self.get_urls(), config=self._config, autoreload=False)
        # manually add asyncio_loop since process_config isn't called in tests
        app.asyncio_loop = asyncio.get_event_loop()
        if app.mixpanel_instance is None:
            app.mixpanel_instance = MockMixpanel()
        return app

    def next_tracking_event(self):
        if not isinstance(self._app.mixpanel_instance, MockMixpanel):
            raise Exception("Can only test tracking events without configuration")
        return self._app.mixpanel_instance.events.get()

    def get_urls(self):
        raise NotImplementedError

    def tearDown(self):
        super(AsyncHandlerTest, self).tearDown()

    def fetch(self, req, **kwargs):
        if 'body' in kwargs and isinstance(kwargs['body'], dict):
            kwargs.setdefault('headers', {})['Content-Type'] = "application/json"
            kwargs['body'] = tornado.escape.json_encode(kwargs['body'])
        # default raise_error to false
        if 'raise_error' not in kwargs:
            kwargs['raise_error'] = False

        return self.http_client.fetch(self.get_url(req), self.stop, **kwargs)

    def assertResponseCodeEqual(self, response, expected_code, message=None):
        """Asserts that the response code was what was expected, with the addition
        that if a 599 is returned (either a timeout or a local exception it will
        rethrow that exception"""

        if response.code == 599 and expected_code != 599:
            response.rethrow()

        self.assertEqual(response.code, expected_code, message)

    def fetch_signed(self, path, *, signing_key=None, signature=None, timestamp=None, address=None, **kwargs):

        if not isinstance(path, str) or not path.startswith("/"):
            # for simplicity's sake, don't accept HTTPRequest objects or external urls in the tests
            raise Exception("first argument must be path string starting with a / (e.g. /v1/tx)")

        # find out if there's a path prefix added by get_url
        prefix = "/{}".format(self.get_url(path).split('/', 3)[-1]).split(path)[0]

        headers = kwargs.setdefault('headers', tornado.httputil.HTTPHeaders())

        if 'body' in kwargs:
            body = kwargs.pop('body')
            if isinstance(body, dict):
                headers['Content-Type'] = "application/json"
                body = tornado.escape.json_encode(body).encode('utf-8')
            elif isinstance(body, str):
                # try and find the charset to use to encode this
                if 'Content-Type' in headers:
                    idx = headers['Content-Type'].find('charset=')
                    if idx >= 0:
                        charset = headers['Content-Type'][idx + 8:]
                        idx = charset.find(';')
                        if idx >= 0:
                            charset = charset[:idx]
                    else:
                        charset = 'utf-8'
                else:
                    charset = 'utf-8'
                # encode to a byte string
                body = body.encode(charset)
            elif not isinstance(body, bytes):
                raise Exception("Unable to handle bodys of type '{}'".format(type(body)))
        else:
            body = None

        method = kwargs.setdefault('method', 'GET').upper()

        if signing_key is None and (address is None or signature is None):
            raise Exception("signing_key is required unless address and signature is given")

        if timestamp is None and signature is not None:
            raise Exception("timestamp is required if signature is given explicitly")

        if address is None:
            address = private_key_to_address(signing_key)
        if timestamp is None:
            timestamp = int(time.time())
        if signature is None:
            signature = sign_request(signing_key, method, "{}{}".format(prefix, path), timestamp, body)

        headers[TOSHI_ID_ADDRESS_HEADER] = address
        headers[TOSHI_SIGNATURE_HEADER] = signature
        headers[TOSHI_TIMESTAMP_HEADER] = str(timestamp)

        # because tornado doesn't like POSTs with body set to None
        if body is None and method == "POST":
            body = b""

        return self.fetch(path, body=body, **kwargs)
