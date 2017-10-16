import asyncio
import concurrent.futures
import tornado.ioloop
import tornado.options
import tornado.web

from dgas.log import log
from dgas.config import config

class Application(tornado.web.Application):

    def __init__(self, urls, **kwargs):

        cookie_secret = kwargs.pop('cookie_secret', None)
        if cookie_secret is None:
            cookie_secret = config['general'].get('cookie_secret', None)

        super(Application, self).__init__(
            urls, debug=config['general'].getboolean('debug'),
            cookie_secret=cookie_secret, **kwargs)

        if 'executor' in config:
            max_workers = config['executor'].getint('max_workers', None)
        else:
            max_workers = None

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

        if 'mixpanel' in config and 'token' in config['mixpanel']:
            try:
                from dgas.analytics import TornadoMixpanelConsumer
                import mixpanel
                self.mixpanel_consumer = TornadoMixpanelConsumer()
                self.mixpanel_instance = mixpanel.Mixpanel(config['mixpanel']['token'], consumer=self.mixpanel_consumer)
            except:
                log.warning("Mixpanel is configured, but the mixpanel-python library hasn't been installed")
                self.mixpanel_instance = None
        else:
            self.mixpanel_instance = None

    async def _start(self):
        if 'database' in config:
            from dgas.database import prepare_database
            await prepare_database()
        if 'redis' in config:
            from dgas.redis import prepare_redis
            await prepare_redis()
        self.listen(tornado.options.options.port, xheaders=True)
        log.info("Starting HTTP Server on port: {}".format(tornado.options.options.port))

    def start(self):
        asyncio.get_event_loop().create_task(self._start())
        asyncio.get_event_loop().run_forever()
