import asyncpg.test.base
import tornado.escape
import tornado.httputil
import time

from dgasio.crypto import private_key_to_address
from dgasio.request import sign_request

from tokenservices.handlers import TOKEN_TIMESTAMP_HEADER, TOKEN_SIGNATURE_HEADER, TOKEN_ID_ADDRESS_HEADER

class AsyncHandlerTest(asyncpg.test.base.AsyncHandlerTest):

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

        headers[TOKEN_ID_ADDRESS_HEADER] = address
        headers[TOKEN_SIGNATURE_HEADER] = signature
        headers[TOKEN_TIMESTAMP_HEADER] = str(timestamp)

        # because tornado doesn't like POSTs with body set to None
        if body is None and method == "POST":
            body = b""

        return super().fetch(path, body=body, **kwargs)
