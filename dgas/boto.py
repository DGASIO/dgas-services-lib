import asyncio
import aiobotocore
from dgas.config import config

class BotoContext:

    __slots__ = ('_session', '_client', '_config', '_default_bucket')

    def __init__(self, handler):
        if not hasattr(handler.application, '_botosession'):
            handler.application._botosession = \
                aiobotocore.get_session(loop=asyncio.get_event_loop())
        self._session = handler.application._botosession
        self._client = None
        self._config = {k: v for k, v in config['s3'].items() if k != 'bucket_name'}
        if 'bucket_name' in config['s3']:
            self._default_bucket = config['s3']['bucket_name']
        else:
            self._default_bucket = None

    async def __aenter__(self):
        if self._client is not None:
            raise Exception("Client already exists")
        self._client = self._session.create_client(
            's3', **self._config)
        return self

    async def __aexit__(self, extype, ex, tb):
        try:
            await self._client.close()
        finally:
            self._client = None

    async def put_object(self, *, key, body, bucket=None):
        if bucket is None:
            if self._default_bucket:
                bucket = self._default_bucket
            else:
                raise Exception("No default for bucket in s3 config")
        return await asyncio.ensure_future(
            self._client.put_object(Bucket=bucket,
                                    Key=key,
                                    Body=body))

    async def delete_object(self, key, bucket=None):
        if bucket is None:
            if self._default_bucket:
                bucket = self._default_bucket
            else:
                raise Exception("No default for bucket in s3 config")
        return await asyncio.ensure_future(
            self._client.delete_object(Bucket=bucket,
                                       Key=key))

    async def head_object(self, key, bucket=None):
        if bucket is None:
            if self._default_bucket:
                bucket = self._default_bucket
            else:
                raise Exception("No default for bucket in s3 config")
        return await asyncio.ensure_future(
            self._client.head_object(Bucket=bucket,
                                     Key=key))

    async def get_object(self, key, bucket=None):
        if bucket is None:
            if self._default_bucket:
                bucket = self._default_bucket
            else:
                raise Exception("No default for bucket in s3 config")
        return await asyncio.ensure_future(
            self._client.get_object(Bucket=bucket,
                                    Key=key))

    async def list_objects(self, bucket=None):
        if bucket is None:
            if self._default_bucket:
                bucket = self._default_bucket
            else:
                raise Exception("No default for bucket in s3 config")
        return await asyncio.ensure_future(
            self._client.list_objects(Bucket=bucket))

    def url_for_object(self, key, bucket=None, signed=False):
        if bucket is None:
            if self._default_bucket:
                bucket = self._default_bucket
            else:
                raise Exception("No default for bucket in s3 config")
        url = self._client.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key})
        if not signed:
            return url.split('?', 1)[0]

class BotoMixin:

    @property
    def boto(self):
        if not hasattr(self, '_botocontext'):
            self._botocontext = BotoContext(self)
        return self._botocontext
