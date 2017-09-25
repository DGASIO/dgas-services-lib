import os
import regex
import time
import tornado.escape
import tornado.web
import traceback

from .utils import validate_signature, validate_address, parse_int
from .request import generate_request_signature_data_string
from .ethereum.utils import data_decoder, ecrecover
from .errors import JSONHTTPError
from .analytics import encode_id
from .log import log
from json import JSONDecodeError

DEFAULT_JSON_ARGUMENT = object()

# used to validate the timestamp in requests. if the difference between
# the timestamp and the current time is greater than this the reuqest
# is rejected
TIMESTAMP_EXPIRY = int(os.environ.get('TIMESTAMP_EXPIRY', 180))

# TOKEN auth header variable names
TOKEN_TIMESTAMP_HEADER = "Token-Timestamp"
TOKEN_SIGNATURE_HEADER = "Token-Signature"
TOKEN_ID_ADDRESS_HEADER = "Token-ID-Address"

TOKEN_TIMESTAMP_QUERY_ARG = "tokenTimestamp"
TOKEN_SIGNATURE_QUERY_ARG = "tokenSignature"
TOKEN_ID_ADDRESS_QUERY_ARG = "tokenIdAddress"

TOSHI_TIMESTAMP_HEADER = "Dgas-Timestamp"
TOSHI_SIGNATURE_HEADER = "Dgas-Signature"
TOSHI_ID_ADDRESS_HEADER = "Dgas-ID-Address"

TOSHI_TIMESTAMP_QUERY_ARG = "dgasTimestamp"
TOSHI_SIGNATURE_QUERY_ARG = "dgasSignature"
TOSHI_ID_ADDRESS_QUERY_ARG = "dgasIdAddress"


class RequestVerificationMixin:

    def verify_request(self):
        """Verifies that the signature and the payload match the expected address
        raising a JSONHTTPError (400) if something is wrong with the request"""

        if TOSHI_ID_ADDRESS_HEADER in self.request.headers:
            expected_address = self.request.headers[TOSHI_ID_ADDRESS_HEADER]
        elif self.get_argument(TOSHI_ID_ADDRESS_QUERY_ARG, None):
            expected_address = self.get_argument(TOSHI_ID_ADDRESS_QUERY_ARG)
        elif TOKEN_ID_ADDRESS_HEADER in self.request.headers:
            expected_address = self.request.headers[TOKEN_ID_ADDRESS_HEADER]
        elif self.get_argument(TOKEN_ID_ADDRESS_QUERY_ARG, None):
            expected_address = self.get_argument(TOKEN_ID_ADDRESS_QUERY_ARG)
        else:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing Dgas-ID-Address'}]})

        if TOSHI_SIGNATURE_HEADER in self.request.headers:
            signature = self.request.headers[TOSHI_SIGNATURE_HEADER]
        elif self.get_argument(TOSHI_SIGNATURE_QUERY_ARG, None):
            signature = self.get_argument(TOSHI_SIGNATURE_QUERY_ARG)
        elif TOKEN_SIGNATURE_HEADER in self.request.headers:
            signature = self.request.headers[TOKEN_SIGNATURE_HEADER]
        elif self.get_argument(TOKEN_SIGNATURE_QUERY_ARG, None):
            signature = self.get_argument(TOKEN_SIGNATURE_QUERY_ARG)
        else:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing Dgas-Signature'}]})

        if TOSHI_TIMESTAMP_HEADER in self.request.headers:
            timestamp = self.request.headers[TOSHI_TIMESTAMP_HEADER]
        elif self.get_argument(TOSHI_TIMESTAMP_QUERY_ARG, None):
            timestamp = self.get_argument(TOSHI_TIMESTAMP_QUERY_ARG)
        elif TOKEN_TIMESTAMP_HEADER in self.request.headers:
            timestamp = self.request.headers[TOKEN_TIMESTAMP_HEADER]
        elif self.get_argument(TOKEN_TIMESTAMP_QUERY_ARG, None):
            timestamp = self.get_argument(TOKEN_TIMESTAMP_QUERY_ARG)
        else:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing Dgas-Timestamp'}]})

        timestamp = parse_int(timestamp)
        if timestamp is None:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_timestamp',
                                                       'message': 'Given Dgas-Timestamp is invalid'}]})

        if not validate_address(expected_address):
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_id_address', 'message': 'Invalid Dgas-ID-Address'}]})

        if not validate_signature(signature):
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Dgas-Signature'}]})

        try:
            signature = data_decoder(signature)
        except Exception:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Dgas-Signature'}]})

        verb = self.request.method
        uri = self.request.path

        if self.request.body:
            datahash = self.request.body
        else:
            datahash = ""

        data_string = generate_request_signature_data_string(verb, uri, timestamp, datahash)

        if not ecrecover(data_string, signature, expected_address):
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Dgas-Signature'}]})

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

        count_token_headers = sum(1 if x in self.request.headers else 0 for x in [TOKEN_ID_ADDRESS_HEADER, TOKEN_SIGNATURE_HEADER, TOKEN_TIMESTAMP_HEADER])
        count_dgas_headers = sum(1 if x in self.request.headers else 0 for x in [TOSHI_ID_ADDRESS_HEADER, TOSHI_SIGNATURE_HEADER, TOSHI_TIMESTAMP_HEADER])

        if count_token_headers == 3 or count_dgas_headers == 3:
            return True
        if count_token_headers == 0 or count_dgas_headers == 0:
            return False
        if raise_if_partial:
            raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Missing headers required for authentication'}]})

class JsonBodyMixin:

    @property
    def json(self):
        if not hasattr(self, '_json'):
            mimetype = self.request.headers['Content-Type'].lower()
            if mimetype.startswith('application/json'):
                encoding = 'utf-8'
                if mimetype[16:].startswith("; charset="):
                    encoding = mimetype[26:]
                try:
                    data = self.request.body.decode(encoding).strip()
                    self._json = tornado.escape.json_decode(data) if data else {}
                except (LookupError, UnicodeDecodeError, JSONDecodeError):
                    self._json = {}
            else:
                self._json = {}
        return self._json

    def get_json_argument(self, name, default=DEFAULT_JSON_ARGUMENT):
        if name not in self.json:
            if default is DEFAULT_JSON_ARGUMENT:
                raise JSONHTTPError(400, "missing_arguments")
            return default
        return self.json[name]

class BaseHandler(JsonBodyMixin, tornado.web.RequestHandler):

    def prepare(self):

        # log the full request and headers if the log level is set to debug
        if log.level == 10:
            log.debug("Preparing request: {} {}".format(self.request.method, self.request.path))
            for k, v in self.request.headers.items():
                log.debug("{}: {}".format(k, v))

        if 'X-Forwarded-Proto' in self.request.headers:
            proto = self.request.headers['X-Forwarded-Proto']
        else:
            proto = self.request.protocol
        if proto != 'https' and 'enforce_https' in self.application.config['general']:
            mode = self.application.config['general']['enforce_https']
            if mode == 'reject':
                self.set_status(404)
                self.finish()
            else:
                # default to redirect
                self.redirect(regex.sub(r'^([^:]+)', 'https', self.request.full_url()), permanent=True)

        return super().prepare()

    def write_error(self, status_code, **kwargs):
        """Overrides tornado's default error writing handler to return json data instead of a html template"""
        rval = {'type': 'error', 'payload': {}}
        if 'exc_info' in kwargs:
            # check exc type and if JSONHTTPError check for extra details
            exc_type, exc_value, exc_traceback = kwargs['exc_info']
            if isinstance(exc_value, JSONHTTPError):
                if exc_value.body is not None:
                    rval = exc_value.body
                elif exc_value.code is not None:
                    rval['payload']['code'] = exc_value.code
            # if we're in debug mode, add the exception data to the response
            if self.application.config['general'].getboolean('debug'):
                rval['exc_info'] = traceback.format_exception(*kwargs["exc_info"])
        log.error(rval)
        self.write(rval)

    def run_in_executor(self, func, *args):
        return self.application.asyncio_loop.run_in_executor(self.application.executor, func, *args)

class GenerateTimestamp(BaseHandler):

    def get(self):
        self.write({"timestamp": int(time.time())})
