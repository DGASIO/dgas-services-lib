import asyncio
import os
import tornado.httpclient
import tornado.escape
import aiobotocore
from dgas.boto import BotoContext

from testing.common.database import (
    Database, get_path_of
)

class MotoServer(Database):

    DEFAULT_SETTINGS = dict(auto_start=2,
                            base_dir=None,
                            moto_server=None,
                            port=None,
                            copy_data_from=None)

    subdirectories = ['data', 'tmp']

    def initialize(self):
        self.moto_server = self.settings.get('moto_server')
        if self.moto_server is None:
            self.moto_server = get_path_of('moto_server')

    def get_data_directory(self):
        return os.path.join(self.base_dir, 'data')

    def get_server_commandline(self):
        cmd = [self.moto_server, 's3',
               "-p{}".format(self.settings['port'])]
        return cmd

    def dsn(self):
        return {'endpoint_url': 'http://127.0.0.1:{}'.format(self.settings['port']),
                'aws_access_key_id': 'xxx',
                'aws_secret_access_key': 'xxx'}

    def is_server_available(self):
        try:
            resp = tornado.httpclient.HTTPClient().fetch(
                self.dsn()['endpoint_url'],
                method="GET",
                raise_error=False
            )
            return resp.code == 200
        except Exception as e:
            print(e)
            return False


def requires_moto(func=None, pass_moto_server=False):

    def wrap(fn):

        async def wrapper(self, *args, **kwargs):

            moto = MotoServer()

            self._app.config['s3'] = moto.dsn()
            session = aiobotocore.get_session(loop=asyncio.get_event_loop())
            dsn = moto.dsn()
            service_name = 's3'
            self._app.config['s3']['bucket_name'] = bucket = 'testing-bucket-1'
            async with session.create_client(service_name, **dsn) as client:
                await asyncio.ensure_future(client.create_bucket(Bucket=bucket, ACL='public-read'))

            if pass_moto_server:
                kwargs['moto_server'] = moto

            try:
                f = fn(self, *args, **kwargs)
                if asyncio.iscoroutine(f):
                    await f
            finally:
                moto.stop()

        return wrapper

    if func is not None:
        return wrap(func)
    else:
        return wrap

class BotoTestContext(BotoContext):
    def __init__(self, handler):
        if not hasattr(handler._app, '_botosession'):
            handler._app._botosession = \
                aiobotocore.get_session(loop=asyncio.get_event_loop())
        self._session = handler._app._botosession
        self._client = None
        self._config = {k: v for k, v in handler._app.config['s3'].items() if k != 'bucket_name'}
        if 'bucket_name' in handler._app.config['s3']:
            self._default_bucket = handler._app.config['s3']['bucket_name']
        else:
            self._default_bucket = None


class BotoTestMixin:
    @property
    def boto(self):
        if not hasattr(self, '_botocontext'):
            self._botocontext = BotoTestContext(self)
        return self._botocontext
