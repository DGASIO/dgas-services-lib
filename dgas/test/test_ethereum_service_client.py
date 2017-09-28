import unittest
import json

from multiprocessing import Process

from .utils import get_unused_port

from http.server import HTTPServer, BaseHTTPRequestHandler

from dgas.utils import parse_int, validate_address
from dgas.clients import EthereumServiceClient
from dgas.ethereum.utils import data_decoder, data_encoder
from dgas.ethereum.tx import (
    DEFAULT_STARTGAS, create_transaction,
    encode_transaction, decode_transaction,
    add_signature_to_transaction
)

DEFAULT_GASPRICE = 20000000000

class MockEthereumServiceRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == '/test':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"HELLO")
            return

        if self.path.startswith('/v1/balance/'):
            address = self.path[12:]
            if address.endswith("/"):
                address = address[:-1]

            if address == "0x0004DE837Ea93edbE51c093f45212AB22b4B35fc":
                confirmed = 48857277160882581789
                unconfirmed = 48857277160880000000
            else:
                confirmed = 0
                unconfirmed = 0

            self.write_data(200, {
                "confirmed_balance": hex(confirmed),
                "unconfirmed_balance": hex(unconfirmed)
            })
            return

        self.send_error(404)
        self.end_headers()

    def write_data(self, code, data):

        if code >= 400:
            self.send_error(code)
        else:
            self.send_response(code)

        if data:
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.end_headers()

    def do_POST(self):

        # TODO: figure out why read is blocking here
        data = self.rfile.read(len(self.rfile.peek()))
        data = data.decode('utf-8')
        data = json.loads(data)

        if self.path == "/v1/tx/skel":

            gas_price = parse_int(data['gas_price']) if 'gas_price' in data else DEFAULT_GASPRICE
            gas = parse_int(data['gas']) if 'gas' in data else DEFAULT_STARTGAS
            nonce = parse_int(data['nonce']) if 'nonce' in data else 0

            if 'value' not in data or 'from' not in data or 'to' not in data:
                self.write_data(400, {'errors': [{'id': 'bad_arguments', 'message': 'Bad Arguments'}]})
                return
            value = parse_int(data['value'])
            to_address = data['to']
            from_address = data['from']

            if not validate_address(to_address):
                self.write_data(400, {'errors': [{'id': 'invalid_to_address', 'message': 'Invalid To Address'}]})
                return
            if not validate_address(from_address):
                self.write_data(400, {'errors': [{'id': 'invalid_from_address', 'message': 'Invalid From Address'}]})
                return

            tx = create_transaction(nonce=nonce, gasprice=gas_price, startgas=gas,
                                    to=to_address, value=value)

            transaction = encode_transaction(tx)

            self.write_data(200, {
                "tx_data": {
                    "nonce": hex(nonce),
                    "from": from_address,
                    "to": to_address,
                    "value": hex(value),
                    "startGas": hex(gas),
                    "gasPrice": hex(gas_price)
                },
                "tx": transaction
            })

        elif self.path == "/v1/tx":

            tx = decode_transaction(data['tx'])

            if 'signature' in data:

                sig = data_decoder(data['signature'])

                add_signature_to_transaction(tx, sig)

            self.write_data(200, {"tx_hash": data_encoder(tx.hash)})

        else:

            self.write_data(404)

class TestEthereumServiceClient(unittest.TestCase):

    def setUp(self):
        server_address = ('', get_unused_port())
        url = "http://localhost:{}".format(server_address[1])
        self.service_client = EthereumServiceClient(url)

        self.httpd = HTTPServer(server_address, MockEthereumServiceRequestHandler)
        self.httpd_thread = Process(target=self.httpd.serve_forever, args=())
        self.httpd_thread.start()

    def tearDown(self):
        self.httpd_thread.terminate()

    def test_get_skel(self):

        tx = self.service_client.generate_tx_skel(
            "0x0004DE837Ea93edbE51c093f45212AB22b4B35fc",
            "0xdb089a4f9a8c5f17040b4fc51647e942b5fc601d",
            1000000000000000000,
            timeout=5)

        self.assertEqual(encode_transaction(tx), "0xe9808504a817c80082520894db089a4f9a8c5f17040b4fc51647e942b5fc601d880de0b6b3a764000080")

    def test_send_tx(self):

        tx = decode_transaction("0xe9808504a817c80082520894db089a4f9a8c5f17040b4fc51647e942b5fc601d880de0b6b3a764000080")
        sig = "0xf5a43adea07d366ae420a5c75a5cae6c60d3e4aaa0b72c2f37fc387efd43d7fd30c4327f2dbd959f654857f58912129b09763329459d08e25547d895ae90fa0f01"

        resp = self.service_client.send_tx(tx, sig)

        self.assertEqual(resp, "0x07ca664267650c87c11318710e3afa2f8f191814d25def8e0c4f2768f3ef5ccb")

    def test_balance(self):

        confirmed, unconfirmed = self.service_client.get_balance("0x0004DE837Ea93edbE51c093f45212AB22b4B35fc")

        self.assertEqual(confirmed, 48857277160882581789)
        self.assertEqual(unconfirmed, 48857277160880000000)

    # TODO: test error responses
