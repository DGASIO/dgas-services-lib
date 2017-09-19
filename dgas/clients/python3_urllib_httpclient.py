import urllib.request
import urllib.error
import socket

from .base import DgasHTTPClientBase, DgasHTTPResponse
from io import BytesIO
import time

class DgasHTTPClient(DgasHTTPClientBase):

    def fetch_impl(self, request):
        req = urllib.request.Request(
            request.url, method=request.method,
            data=request.body, headers=request.headers)

        start_time = time.time()
        try:

            resp = urllib.request.urlopen(req, timeout=request.timeout)

        except urllib.error.HTTPError as e:

            resp = e

        except socket.timeout as e:

            return DgasHTTPResponse(request, 599)

        end_time = time.time()

        code = resp.code
        buffer = BytesIO(resp.read())
        headers = dict(resp.info())

        return DgasHTTPResponse(request, code, headers=headers, buffer=buffer, request_time=end_time - start_time)
