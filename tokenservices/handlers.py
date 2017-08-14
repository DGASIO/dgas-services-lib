import time
from asyncpg.handlers import BaseHandler
from asyncpg.errors import JSONHTTPError
from dgasio.utils import flatten_payload, data_decoder, parse_int
from dgasio.crypto import ecrecover

# used to validate the timestamp in requests. if the difference between
# the timestamp and the current time is greater than this the reuqest
# is rejected
TIMESTAMP_EXPIRY = 15

class GenerateTimestamp(BaseHandler):

    def get(self):
        self.write({"timestamp": int(time.time())})

class RequestVerificationMixin:

    def verify_payload(self, expected_address, signature, payload):

        """Verifies that the signature and the payload match the expected address
        raising a JSONHTTPError (400) if something is wrong with the request"""

        try:
            signature = data_decoder(signature)
        except Exception:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Signature'}]})

        address = ecrecover(flatten_payload(payload), signature)

        if address is None or address != expected_address:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Signature'}]})

        # check timestamp
        if 'timestamp' not in payload:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_timestamp', 'message': 'The difference between the timestamp and the current time is too large'}]})

        timestamp = parse_int(payload['timestamp'])
        if timestamp is None or abs(int(time.time()) - timestamp) > TIMESTAMP_EXPIRY:
            raise JSONHTTPError(400, body={'errors': [{'id': 'invalid_signature', 'message': 'Invalid Signature'}]})