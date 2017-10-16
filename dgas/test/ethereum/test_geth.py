from dgas.test.base import AsyncHandlerTest
from tornado.testing import gen_test

from dgas.test.ethereum.geth import requires_geth, geth_websocket_connect

class GethTest(AsyncHandlerTest):

    def get_urls(self):
        return []

    @gen_test(timeout=10)
    @requires_geth(ws=True, pass_server=True)
    async def test_geth_ws(self, *, geth):

        ws_con = await geth_websocket_connect(geth.dsn()['ws'])

        ws_con.write_message('{"id": 1, "method": "eth_subscribe", "params": ["newHeads", {}]}')

        await ws_con.read_message()

        ws_con.close()
