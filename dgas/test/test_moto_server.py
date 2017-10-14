import asyncio
import aiobotocore

from .base import AsyncHandlerTest

from dgas.test.moto_server import requires_moto
from tornado.testing import gen_test


class MotoServerTest(AsyncHandlerTest):

    def get_urls(self):
        return []

    @gen_test(timeout=30)
    @requires_moto(pass_moto_server=True)
    async def test_moto_connection(self, *, moto_server):

        key = 'test-key-1'
        dsn = moto_server.dsn()
        bucket = self._app.config['s3']['bucket']
        data = b'\x01' * 1024

        session = aiobotocore.get_session(loop=asyncio.get_event_loop())
        async with session.create_client('s3', **dsn) as client:
            await asyncio.ensure_future(
                client.put_object(Bucket=bucket,
                                  Key=key,
                                  Body=data))
        resp = await self.fetch("{}/{}/{}".format(dsn['endpoint_url'], bucket, key))
        self.assertEqual(resp.body, data)
