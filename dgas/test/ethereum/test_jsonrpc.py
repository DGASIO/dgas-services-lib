from ..base import AsyncHandlerTest
from dgas.handlers import BaseHandler
from dgas.ethereum import EthereumMixin
from tornado.testing import gen_test

from .parity import requires_parity, FAUCET_ADDRESS

class Handler(EthereumMixin, BaseHandler):

    async def get(self):

        balance = await self.eth.eth_getBalance(FAUCET_ADDRESS)
        self.write(str(balance))

class EthTest(AsyncHandlerTest):

    def get_urls(self):
        return [(r'^/$', Handler)]

    @gen_test
    @requires_parity
    async def test_jsonrpc_connection(self):

        resp = await self.fetch('/')
        self.assertEqual(resp.body, b'1606938044258990275541962092341162602522202993782792835301376')
