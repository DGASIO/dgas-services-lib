import sys
import json

if sys.version_info[:2] < (3,):
    FILE_TYPE = file # noqa
else:
    import io
    FILE_TYPE = io.IOBase

class DgasHTTPClientBase:

    def fetch(self, url, method="GET", body=None, headers=None, timeout=None):
        if not isinstance(url, DgasHTTPRequest):
            req = DgasHTTPRequest(url, method=method, body=body, headers=headers, timeout=timeout)
        else:
            req = url
        return self.fetch_impl(req)

    def fetch_impl(self, request):
        raise NotImplementedError()

class DgasHTTPRequest:

    def __init__(self, url, method="GET", body=None, headers=None, timeout=20):
        if headers is None:
            headers = {}
        if body:
            if isinstance(body, dict):
                body = json.dumps(body).encode('utf-8')
                headers['Content-Type'] = 'application/json'
                headers['Content-Length'] = len(body)
            elif isinstance(body, FILE_TYPE):
                body = body.read()
                if isinstance(body, str):
                    body = body.encode('utf-8')
                headers['Content-Length'] = str(len(body))
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'application/octet-stream'
            # else leave body as is

        self.url = url
        self.method = method
        self.body = body
        self.headers = headers
        self.timeout = timeout

    def __repr__(self):
        return "{} {}\n{}\n{}".format(
            self.method, self.url,
            '\n'.join(["{}: {}".format(k, v) for k, v in self.headers.items()]),
            (self.body or b'').decode('utf-8'))

class DgasHTTPResponse:

    def __init__(self, request, code, headers=None, buffer=None, request_time=None):

        self.code = code
        if headers is not None:
            self.headers = headers
        else:
            self.headers = {}
        self.buffer = buffer
        self._body = None
        self.request_time = request_time

    @property
    def body(self):
        if self.buffer is None:
            return None
        elif self._body is None:
            self._body = self.buffer.getvalue()

        return self._body
