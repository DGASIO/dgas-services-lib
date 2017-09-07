from .python3_urllib_httpclient import TokenHTTPClient
import json

from ethereum.transactions import Transaction, UnsignedTransaction
from tokenservices.ethereum.tx import encode_transaction, decode_transaction
from tokenservices.utils import parse_int

class EthereumServiceClient:

    def __init__(self, base_url=None):

        if base_url is None:
            base_url = "https://token-eth-service.herokuapp.com"

        self.base_url = base_url
        self._client = TokenHTTPClient()

    def _fetch(self, path, method, body=None, **kwargs):

        resp = self._client.fetch(
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

    def get_balance(self, address, **kwargs):

        resp = self._fetch("/v1/balance/{}".format(address), "GET", **kwargs)
        return parse_int(resp["confirmed_balance"]), parse_int(resp["unconfirmed_balance"])

    def generate_tx_skel(self, from_address, to_address, value, gas=None, gas_price=None, nonce=None, data=None, **kwargs):

        reqdata = {"from": from_address, "to": to_address, "value": value}
        if gas is not None:
            reqdata['gas'] = gas
        if gas_price is not None:
            reqdata['gas_price'] = gas_price
        if nonce is not None:
            reqdata['nonce'] = nonce
        if data is not None:
            reqdata['data'] = data

        resp = self._fetch("/v1/tx/skel", "POST", reqdata, **kwargs)
        return decode_transaction(resp['tx'])

    def send_tx(self, tx, signature=None, **kwargs):

        if isinstance(tx, (Transaction, UnsignedTransaction)):
            tx = encode_transaction(tx)

        body = {"tx": tx}
        if signature:
            body['signature'] = signature

        resp = self._fetch("/v1/tx", "POST", body, **kwargs)
        return resp['tx_hash']
