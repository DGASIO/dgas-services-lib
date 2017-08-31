import time
import asyncio
from asyncpg.handlers import BaseHandler
from asyncpg.errors import JSONHTTPError
from ethutils import data_decoder
from dgasio.utils import validate_signature, validate_address, parse_int
from dgasio.crypto import ecrecover
from dgasio.request import generate_request_signature_data_string
from tornado.ioloop import IOLoop
from functools import partial

# used to validate the timestamp in requests. if the difference between
# the timestamp and the current time is greater than this the reuqest
# is rejected
TIMESTAMP_EXPIRY = 15

# TOKEN auth header variable names
TOKEN_TIMESTAMP_HEADER = "Token-Timestamp"
TOKEN_SIGNATURE_HEADER = "Token-Signature"
TOKEN_ID_ADDRESS_HEADER = "Token-ID-Address"

TOKEN_TIMESTAMP_QUERY_ARG = "tokenTimestamp"
TOKEN_SIGNATURE_QUERY_ARG = "tokenSignature"
TOKEN_ID_ADDRESS_QUERY_ARG = "tokenIdAddress"

class GenerateTimestamp(BaseHandler):

    def get(self):
        self.write({"timestamp": int(time.time())})

class RequestVerificationMixin:

    def verify_request(self):
        """Verifies that the signature and the payload match the expected address
        raising a JSONHTTPError (400) if something is wrong with the request"""

        if TOKEN_ID_ADDRESS_HEADER in self.request.headers:
            expected_address = self.request.headers[TOKEN_ID_ADDRESS_HEADER]
        elif self.get_argument(TOKEN_ID_ADDRESS_QUERY_ARG, None):
            expected_address = self.get_argument(TOKEN_ID_ADDRESS_QUERY_ARG)
        else:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing Token-ID-Address'}]})

        if TOKEN_SIGNATURE_HEADER in self.request.headers:
            signature = self.request.headers[TOKEN_SIGNATURE_HEADER]
        elif self.get_argument(TOKEN_SIGNATURE_QUERY_ARG, None):
            signature = self.get_argument(TOKEN_SIGNATURE_QUERY_ARG)
        else:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing Token-Signature'}]})

        if TOKEN_TIMESTAMP_HEADER in self.request.headers:
            timestamp = self.request.headers[TOKEN_TIMESTAMP_HEADER]
        elif self.get_argument(TOKEN_TIMESTAMP_QUERY_ARG, None):
            timestamp = self.get_argument(TOKEN_TIMESTAMP_QUERY_ARG)
        else:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing Token-Timestamp'}]})

        timestamp = parse_int(timestamp)
        if timestamp is None:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_timestamp',
                                                       'message': 'Given Token-Timestamp is invalid'}]})

        if not validate_address(expected_address):
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_id_address', 'message': 'Invalid Token-ID-Address'}]})

        if not validate_signature(signature):
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Token-Signature'}]})

        try:
            signature = data_decoder(signature)
        except Exception:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Token-Signature'}]})

        verb = self.request.method
        uri = self.request.path

        if self.request.body:
            datahash = self.request.body
        else:
            datahash = ""

        data_string = generate_request_signature_data_string(verb, uri, timestamp, datahash)

        if not ecrecover(data_string, signature, expected_address):
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Token-Signature'}]})

        if abs(int(time.time()) - timestamp) > TIMESTAMP_EXPIRY:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_timestamp',
                                                       'message': 'The difference between the timestamp and the current time is too large'}]})

        return expected_address

    def is_request_signed(self, raise_if_partial=True):
        """Returns true if the request contains the headers needed to be considered signed.
        Designed for use in situations where a signature may be optional.

        if `raise_if_partial` is true (default) this will raise a HTTPError if the
        request contains only some of the headers needed for the signature
        verification, otherwise False will be returned"""

        count_headers = sum(1 if x in self.request.headers else 0 for x in [TOKEN_ID_ADDRESS_HEADER, TOKEN_SIGNATURE_HEADER, TOKEN_TIMESTAMP_HEADER])

        if count_headers == 3:
            return True
        if count_headers == 0:
            return False
        if raise_if_partial:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing headers required for authentication'}]})

DEFAULT_LOGIN_REQUESTS = {}

class LoginAttempt:

    def __init__(self, timeout=60, on_timeout=None):
        self._future = asyncio.Future()
        self._timeout = timeout
        if on_timeout:
            ioloop = IOLoop.current()
            self._looptimeout = ioloop.add_timeout(ioloop.time() + timeout, on_timeout)
        else:
            self._looptimeout = None

    def set_cancelled(self):
        if not self._future.done():
            self._future.set_result(None)

    def cancel_timeout(self):
        if self._looptimeout:
            IOLoop.current().remove_timeout(self._looptimeout)
            self._looptimeout = None

    def set_success(self, address):
        if not self._future.done():
            self._future.set_result(address)

    def set_failed(self, address):
        if not self._future.done():
            self._future.set_result(False)

    def __await__(self):
        return self._future.__await__()

class WebLoginHandler(RequestVerificationMixin, BaseHandler):

    @property
    def login_requests(self):
        return DEFAULT_LOGIN_REQUESTS

    @property
    def login_timeout(self):
        return

    def is_address_allowed(self, address):
        raise NotImplementedError

    def create_new_login_future(self, key, timeout=60):
        if key in self.login_requests:
            self.login_request[key].set_cancelled()
        self.login_requests[key] = LoginAttempt(on_timeout=partial(self.invalidate_login, key))

    def invalidate_login(self, key):
        if key in self.login_requests:
            self.login_requests[key].set_cancelled()
            self.login_requests[key].cancel_timeout()
        del self.login_requests[key]

    def set_login_result(self, key, address):
        if key not in self.login_requests:
            self.create_new_login_future(key)
        if self.is_address_allowed(address):
            self.login_requests[key].set_success(address)
        else:
            self.set_cancelled()

    async def get(self, key):

        if self.is_request_signed():

            address = self.verify_request()
            self.set_login_result(key, address)
            self.set_status(204)

        else:

            if key not in self.login_requests:
                self.create_new_login_future(key)

            address = await self.login_requests[key]

            if address is None:
                raise JSONHTTPError(400, body={'errors': [{'id': 'request_timeout', 'message': 'Login request timed out'}]})
            if address is False:
                raise JSONHTTPError(401, body={'errors': [{'id': 'login_failed', 'message': 'Login failed'}]})

            if hasattr(self, 'on_login'):
                f = self.on_login(address)
                if asyncio.iscoroutine(f):
                    f = await f
                return f
            # else
            self.write({"address": address})
