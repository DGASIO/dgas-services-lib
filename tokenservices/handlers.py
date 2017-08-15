import time
from asyncpg.handlers import BaseHandler
from asyncpg.errors import JSONHTTPError
from dgasio.utils import validate_signature, validate_address, data_decoder, parse_int, flatten_payload
from dgasio.crypto import ecrecover
from dgasio.request import generate_request_signature_data_string

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

    # DEPRECIATED
    def verify_payload(self, expected_address=None, signature=None, payload=None):

        """Verifies that the signature and the payload match the expected address
        raising a JSONHTTPError (400) if something is wrong with the request"""

        if expected_address is None:
            if 'address' in self.json:
                expected_address = self.json['address']
            else:
                raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})

        if signature is None:
            if 'signature' in self.json:
                signature = self.json['signature']
            else:
                raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})

        if payload is None:
            if 'payload' in self.json:
                payload = self.json['payload']
            else:
                raise JSONHTTPError(400, body={'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})

        try:
            signature = data_decoder(signature)
        except Exception:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Signature'}]})

        address = ecrecover(flatten_payload(payload), signature)

        if address is None or address != expected_address:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Signature'}]})

        # check timestamp
        if 'timestamp' not in payload:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_timestamp',
                                                       'message': 'Missing timestamp in payload'}]})

        timestamp = parse_int(payload['timestamp'])
        if timestamp is None:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_timestamp',
                                                       'message': 'Given timestamp is invalid'}]})

        if abs(int(time.time()) - timestamp) > TIMESTAMP_EXPIRY:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_timestamp',
                                                       'message': 'The difference between the timestamp and the current time is too large'}]})

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
