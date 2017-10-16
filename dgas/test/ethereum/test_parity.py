import asyncio

from dgas.test.base import AsyncHandlerTest
from tornado.testing import gen_test
from dgas.config import config

from dgas.ethereum.utils import prepare_ethereum_jsonrpc_client

from .faucet import FaucetMixin
from .parity import ParityServer

class FaucetTest(FaucetMixin, AsyncHandlerTest):

    def get_urls(self):
        return []

    @gen_test(timeout=30)
    async def test_bootnodes(self):

        """Tests that starting two parity instances giving one the first's
        node address as it's bootnode, the two instances communicate"""

        p1 = ParityServer()
        # set the app url so the faucet mixin uses p1
        config['ethereum'] = {'url': p1.dsn()['url']}

        p2 = ParityServer(bootnodes=p1.dsn()['node'])

        p2jsonrpc = prepare_ethereum_jsonrpc_client(p2.dsn())

        addr = '0x39bf9e501e61440b4b268d7b2e9aa2458dd201bb'
        val = 761751855997712

        filter_id = await p2jsonrpc.eth_newPendingTransactionFilter()

        faucet_tx_hash = await self.faucet(addr, val, wait_on_confirmation=False)

        # wait to find if the tx shows up on p2
        found = False
        while not found:
            res = await p2jsonrpc.eth_getFilterChanges(filter_id)
            for tx_hash in res:
                if tx_hash == faucet_tx_hash:
                    found = True
                    break
            else:
                await asyncio.sleep(1)
