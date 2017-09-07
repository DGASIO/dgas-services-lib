import os
import json
from urllib import parse
try:
    import tornado.httpclient
    TORNADO_SUPPORT = True
except:
    TORNADO_SUPPORT = False
    pass

class IdServiceClient:

    def __init__(self, base_url=None, use_tornado=False):

        if base_url is None:
            if 'ID_SERVICE_URL' in os.environ:
                base_url = os.environ['ID_SERVICE_URL'].strip()
            else:
                base_url = "https://token-id-service.herokuapp.com"

        if base_url.endswith('/'):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.tornado = use_tornado
        if use_tornado:
            if TORNADO_SUPPORT is False:
                raise Exception("Unable to use tornado as tornado is not installed")
            self._client = tornado.httpclient.AsyncHTTPClient()
        else:
            #self._client = TokenHTTPClient()
            raise NotImplementedError

    async def _fetch(self, path, method, body=None, **kwargs):

        resp = await self._client.fetch(
            "{}{}".format(self.base_url, path),
            method=method, body=body, **kwargs)

        if resp.body:
            skel = json.loads(resp.body.decode('utf-8'))
        else:
            skel = None

        if resp.code == 200:
            return skel
        else:
            # TODO: better exceptions
            raise Exception(skel or "Got error response: {}".format(resp.code))

    async def get_user(self, address, **kwargs):

        resp = await self._fetch("/v1/user/{}".format(address), "GET", **kwargs)
        return resp

    async def whodis(self, token, **kwargs):

        resp = await self._fetch("/v1/login/verify/{}".format(token), "GET", **kwargs)
        return resp

    async def search_user(self, query, apps=None, offset=0, limit=10, **kwargs):

        args = {"query": query, "offset": offset, "limit": limit}
        if apps is not None:
            args['apps'] = apps

        resp = await self._fetch("/v1/search/user?{}".format(parse.urlencode(args)), "GET", **kwargs)
        return resp
