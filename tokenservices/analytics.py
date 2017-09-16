import asyncio
import base64
import time
import urllib

from hashlib import sha256
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient
from tornado.platform.asyncio import to_asyncio_future

from tokenservices.log import log

class TornadoMixpanelConsumer:

    def __init__(self, events_url=None, people_url=None, import_url=None, request_timeout=None, ioloop=None):
        self._endpoints = {
            'events': events_url or 'https://api.mixpanel.com/track',
            'people': people_url or 'https://api.mixpanel.com/engage',
            'imports': import_url or 'https://api.mixpanel.com/import',
        }
        self._queues = {}
        self._request_timeout = request_timeout

        if ioloop is None:
            ioloop = IOLoop.current()

        self.ioloop = ioloop
        self._api_key = None
        self._httpclient = AsyncHTTPClient()
        self._tasks = []
        for endpoint in self._endpoints:
            self._queues[endpoint] = asyncio.Queue()
            self._tasks.append(asyncio.ensure_future(self.flush(endpoint)))

    def shutdown(self):
        for task in self._tasks:
            task.cancel()

    def send(self, endpoint, json_message, api_key=None):

        if endpoint not in self._endpoints:
            raise Exception('Mixpanel error: No such endpoint "{0}". Valid endpoints are one of {1}'.format(endpoint, self._endpoints.keys()))

        if api_key is not None:
            self._api_key = api_key
        self._queues[endpoint].put_nowait(json_message)

    async def flush(self, endpoint, flush_delay_limit=10, max_size=50):

        last_flush = 0 # 0 so that the first event is always sent
        batch = []
        while True:
            batch.append(await self._queues[endpoint].get())
            while len(batch) < max_size and time.time() - flush_delay_limit < last_flush:
                try:
                    batch.append((await asyncio.wait_for(self._queues[endpoint].get(), 2)))
                except asyncio.TimeoutError:
                    break
            batch_json = '[{0}]'.format(','.join(batch))
            batch = []
            last_flush = time.time()

            data = {
                'data': base64.b64encode(batch_json.encode('utf8')),
                'verbose': 1,
                'ip': 0,
            }
            if self._api_key:
                data.update({'api_key': self._api_key})
            encoded_data = urllib.parse.urlencode(data).encode('utf8')

            resp = await to_asyncio_future(self._httpclient.fetch(
                self._endpoints[endpoint],
                method="POST",
                headers={'Content-Type': "application/x-www-form-urlencoded"},
                body=encoded_data))

            try:
                response = json_decode(resp.body)
                if response['status'] != 1:
                    log.error('Mixpanel error: {0}'.format(response['error']))
            except ValueError:
                log.exception('Cannot interpret Mixpanel server response: {0}'.format(resp.body))

def encode_id(token_id):
    return sha256(token_id.encode('utf-8')).hexdigest() if token_id else None

class AnalyticsMixin:

    def track(self, token_id, event, data=None):
        if self.application.mixpanel_instance:
            self.application.mixpanel_instance.track(encode_id(token_id), event, data)
