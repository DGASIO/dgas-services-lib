import subprocess
import unittest
from ethereum.abi import ContractTranslator
from ethereum.utils import sha3
from tornado.escape import json_decode

from dgas.handlers import BaseHandler
from dgas.ethereum import EthereumMixin
from ..base import AsyncHandlerTest
from tornado.testing import gen_test
from dgas.jsonrpc.client import JsonRPCClient
from testing.common.database import get_path_of

from .parity import requires_parity
from .faucet import FaucetMixin, data_decoder
from .geth import requires_geth

class Handler(EthereumMixin, BaseHandler):

    async def get(self, addr):

        balance = await self.eth.eth_getBalance(addr)
        self.write(str(balance))

class FaucetTest(FaucetMixin, AsyncHandlerTest):

    def get_urls(self):
        return [(r'^/(0x.+)$', Handler)]

    @gen_test(timeout=30)
    @requires_parity
    async def test_parity_faucet_connection(self):

        addr = '0x39bf9e501e61440b4b268d7b2e9aa2458dd201bb'
        val = 761751855997712

        await self.faucet(addr, val)

        resp = await self.fetch('/{}'.format(addr))
        self.assertEqual(resp.body.decode('utf-8'), str(val))

    @gen_test(timeout=30)
    @requires_geth
    async def test_geth_faucet(self):

        addr = '0x39bf9e501e61440b4b268d7b2e9aa2458dd201bb'
        val = 761751855997712

        await self.faucet(addr, val)

        resp = await self.fetch('/{}'.format(addr))
        self.assertEqual(resp.body.decode('utf-8'), str(val))

class ContractTest(FaucetMixin, AsyncHandlerTest):

    def get_urls(self):
        return []

    @unittest.skipIf(get_path_of("solc") is None, "couldn't find solc compiler, skipping test")
    @gen_test(timeout=60)
    @requires_parity(pass_parity='node')
    async def test_deploy_contract(self, *, node):

        client = JsonRPCClient(node.dsn()['url'])

        sourcecode = b"contract greeter{string greeting;function greeter(string _greeting) public{greeting=_greeting;}function greet() constant returns (string){return greeting;}}"
        #source_fn = os.path.join(node.get_data_directory(), 'greeting.sol')
        #with open(source_fn, 'wb') as wf:
        #    wf.write(sourcecode)
        source_fn = '<stdin>'

        contract_name = 'greeter'
        constructor_args = [b'hello world!']

        args = ['solc', '--combined-json', 'bin,abi', '--add-std'] # , source_fn]
        #output = subprocess.check_output(args, stderr=subprocess.PIPE)
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, stderrdata = process.communicate(input=sourcecode)
        output = json_decode(output)

        contract = output['contracts']['{}:{}'.format(source_fn, contract_name)]
        bytecode = data_decoder(contract['bin'])
        contract_interface = json_decode(contract['abi'])

        translator = ContractTranslator(contract_interface)
        constructor_call = translator.encode_constructor_arguments(constructor_args)

        bytecode += constructor_call

        tx_hash, contract_address = await self.deploy_contract(bytecode)

        tx_receipt = await client.eth_getTransactionReceipt(tx_hash)
        self.assertIsNotNone(tx_receipt)

        code = await client.eth_getCode(contract_address)
        self.assertIsNotNone(code)
        self.assertNotEqual(data_decoder(code), b'')

        # call the contract and check the result
        res = await client.eth_call(from_address='0x39bf9e501e61440b4b268d7b2e9aa2458dd201bb', to_address=contract_address, data=sha3('greet()'))
        result = translator.decode_function_result('greet', data_decoder(res))
        self.assertEqual(result[0], constructor_args[0])
