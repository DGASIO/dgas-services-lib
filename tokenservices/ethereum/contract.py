import asyncio
import binascii
import subprocess
import os
import rlp
import json
import ethereum.abi
from tornado.escape import json_decode
from ethereum.transactions import Transaction

from .utils import data_decoder, data_encoder, private_key_to_address
from ..jsonrpc.client import JsonRPCClient

def fix_address_decoding(decoded, types):
    """ethereum library result decoding doesn't add 0x to addresses
    this parses the decoded results and adds 0x to any address types"""
    rval = []
    for val, type in zip(decoded, types):
        if type == 'address':
            rval.append('0x{}'.format(val.decode('ascii')))
        elif type == 'address[]':
            rval.append(['0x{}'.format(v.decode('ascii')) for v in val])
        elif type == 'string':
            rval.append(val.rstrip(b'\x00').decode('utf-8'))
        else:
            rval.append(val)
    return rval

class ContractTranslator(ethereum.abi.ContractTranslator):
    def __init__(self, contract_interface):
        super().__init__(contract_interface)

class ContractMethod:

    def __init__(self, name, contract, *, from_key=None, constant=None):
        self.name = name
        self.contract = contract
        # TODO: forcing const seems to do nothing, since eth_call
        # will just return a tx_hash (on parity at least)
        if constant is None:
            self.is_constant = self.contract.translator.function_data[name]['is_constant']
        else:
            # force constantness of this function
            self.is_constant = constant
        if from_key:
            if isinstance(from_key, str):
                self.from_key = data_decoder(from_key)
            else:
                self.from_key = from_key
            self.from_address = private_key_to_address(from_key)
        else:
            self.from_address = None

    def set_sender(self, key):
        return self.__class__(self.name, self.contract, from_key=key, constant=self.is_constant)

    async def __call__(self, *args, startgas=None, gasprice=20000000000, value=0, wait_for_confirmation=True):

        # TODO: figure out if we can validate args

        ethurl = os.environ.get('ETHEREUM_NODE_URL')
        if not ethurl:
            raise Exception("requires 'ETHEREUM_NODE_URL' environment variable to be set")

        ethclient = JsonRPCClient(ethurl)

        data = self.contract.translator.encode_function_call(self.name, args)

        # TODO: figure out if there's a better way to tell if the function needs to be called via sendTransaction
        if self.is_constant:
            result = await ethclient.eth_call(from_address=self.from_address or '', to_address=self.contract.address,
                                              data=data)
            result = data_decoder(result)
            if result:
                decoded = self.contract.translator.decode_function_result(self.name, result)
                # make sure addresses are encoded as expected
                decoded = fix_address_decoding(decoded, self.contract.translator.function_data[self.name]['decode_types'])
                # return the single value if there is only a single return value
                if len(decoded) == 1:
                    return decoded[0]
                return decoded
            return None

        else:
            if self.from_address is None:
                raise Exception("Cannot call non-constant function without a sender")

            nonce = await ethclient.eth_getTransactionCount(self.from_address)
            balance = await ethclient.eth_getBalance(self.from_address)

            _startgas = await ethclient.eth_estimateGas(self.from_address, self.contract.address, data=data, nonce=nonce, value=value, gasprice=gasprice)
            if startgas is None:
                startgas = _startgas
            if startgas == 50000000:
                # TODO: this is not going to always be the case!
                raise Exception("Unable to estimate gas cost, possibly something wrong with the transaction arguments")

            if balance < (startgas * gasprice):
                raise Exception("Given account doesn't have enough funds")

            tx = Transaction(nonce, gasprice, startgas, self.contract.address, value, data, 0, 0, 0)
            tx.sign(self.from_key)

            tx_encoded = data_encoder(rlp.encode(tx, Transaction))
            try:
                tx_hash = await ethclient.eth_sendRawTransaction(tx_encoded)
            except:
                print(balance, startgas * gasprice, startgas)
                raise

            # wait for the contract to be deployed
            while wait_for_confirmation:
                resp = await ethclient.eth_getTransactionByHash(tx_hash)
                if resp is None or resp['blockNumber'] is None:
                    await asyncio.sleep(0.1)
                else:
                    # TODO: raise exception on error
                    # print("=========================")
                    # print(resp)
                    # receipt = await ethclient.eth_getTransactionReceipt(tx_hash)
                    # print("GAS for {}: Provided: {}, Estimated: {}, Used: {}".format(self.name, startgas, _startgas, int(receipt['gasUsed'][2:], 16)))
                    # print("Estimated gas: {}".format(_startgas))
                    # print("=========================")
                    break

            # TODO: is it possible for non-const functions to have return types?
            return tx_hash


class Contract:

    def __init__(self, *, abi, address, translator=None, creation_tx_hash=None):
        self.abi = abi
        self.valid_funcs = [part['name'] for part in abi if part['type'] == 'function']
        self.translator = translator or ContractTranslator(abi)
        self.address = address
        self.creation_tx_hash = creation_tx_hash

    def __getattr__(self, name):

        if name in self.valid_funcs:
            return ContractMethod(name, self)

        raise AttributeError("'Contract' object has no attribute '{}'".format(name))

    @classmethod
    async def from_source_code(cls, sourcecode, contract_name, constructor_data=None,
                               *, address=None, deployer_private_key=None, import_mappings=None,
                               libraries=None, optimize=False, deploy=True, cwd=None,
                               wait_for_confirmation=True):

        if deploy:
            ethurl = os.environ.get('ETHEREUM_NODE_URL')
            if not ethurl:
                raise Exception("requires 'ETHEREUM_NODE_URL' environment variable to be set")

            if address is None and deployer_private_key is None:
                raise TypeError("requires either address or deployer_private_key")
            if address is None and not isinstance(constructor_data, (list, type(None))):
                raise TypeError("must supply constructor_data as a list (hint: use [] if args should be empty)")

        args = ['solc', '--combined-json', 'bin,abi', '--add-std']
        if libraries:
            args.extend(['--libraries', ','.join(['{}:{}'.format(*library) for library in libraries])])
        if optimize:
            args.append('--optimize')
        if import_mappings:
            args.extend(["{}={}".format(path, mapping) for path, mapping in import_mappings])
        # check if sourcecode is actually a filename
        if cwd:
            filename = os.path.join(cwd, sourcecode)
        else:
            filename = sourcecode
        if os.path.exists(filename):
            args.append(filename)
            sourcecode = None
        else:
            filename = '<stdin>'
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        output, stderrdata = process.communicate(input=sourcecode)
        try:
            output = json_decode(output)
        except json.JSONDecodeError:
            if output and stderrdata:
                output += b'\n' + stderrdata
            elif stderrdata:
                output = stderrdata
            raise Exception("Failed to compile source: {}\n{}\n{}".format(filename, ' '.join(args), output.decode('utf-8')))

        try:
            contract = output['contracts']['{}:{}'.format(filename, contract_name)]
        except KeyError:
            print(output)
            raise
        abi = json_decode(contract['abi'])

        # deploy contract
        translator = ContractTranslator(abi)
        # fix things that don't have a constructor

        if not deploy:
            return Contract(abi=abi,
                            address=address,
                            translator=translator)

        ethclient = JsonRPCClient(ethurl)

        if address is not None:
            # verify there is code at the given address
            for i in range(10):
                code = await ethclient.eth_getCode(address)
                if code == "0x":
                    await asyncio.sleep(1)
                    continue
                break
            else:
                raise Exception("No code found at given address")
            return Contract(abi=abi,
                            address=address,
                            translator=translator)

        try:
            bytecode = data_decoder(contract['bin'])
        except binascii.Error:
            print(contract['bin'])
            raise

        if constructor_data is not None:
            constructor_call = translator.encode_constructor_arguments(constructor_data)
            bytecode += constructor_call

        if isinstance(deployer_private_key, str):
            deployer_private_key = data_decoder(deployer_private_key)
        deployer_address = private_key_to_address(deployer_private_key)
        nonce = await ethclient.eth_getTransactionCount(deployer_address)
        balance = await ethclient.eth_getBalance(deployer_address)

        gasprice = 20000000000
        value = 0

        startgas = await ethclient.eth_estimateGas(deployer_address, '', data=bytecode, nonce=nonce, value=0, gasprice=gasprice)

        if balance < (startgas * gasprice):
            raise Exception("Given account doesn't have enough funds")

        tx = Transaction(nonce, gasprice, startgas, '', value, bytecode, 0, 0, 0)
        tx.sign(deployer_private_key)

        tx_encoded = data_encoder(rlp.encode(tx, Transaction))

        contract_address = data_encoder(tx.creates)

        tx_hash = await ethclient.eth_sendRawTransaction(tx_encoded)

        # wait for the contract to be deployed
        while wait_for_confirmation:
            resp = await ethclient.eth_getTransactionByHash(tx_hash)
            if resp is None or resp['blockNumber'] is None:
                await asyncio.sleep(0.1)
            else:
                code = await ethclient.eth_getCode(contract_address)
                if code == '0x':
                    raise Exception("Failed to deploy contract: resulting address '{}' has no code".format(contract_address))
                break

        return Contract(abi=abi, address=contract_address, translator=translator, creation_tx_hash=tx_hash)

class BoundContract(Contract):
    """A Contract that bound to a specific sender.
    removes the need to call set_sender manually for each transaction"""

    def __init__(self, *, sender, **kwargs):
        self.sender = sender
        super().__init__(**kwargs)

    def __getattr__(self, name):

        attr = super().__getattr__(name)
        if self.sender:
            return attr.set_sender(self.sender)
        return attr
