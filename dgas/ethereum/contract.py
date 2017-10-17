import asyncio
import binascii
import subprocess
import os
import rlp
import json
import ethereum.abi
import time
from tornado.escape import json_decode
from ethereum.transactions import Transaction

from dgas.config import config
from dgas.ethereum.utils import data_decoder, data_encoder, private_key_to_address
from dgas.jsonrpc.client import JsonRPCClient

def get_url():
    ethurl = config['ethereum']['url'] if 'ethereum' in config else os.environ.get('ETHEREUM_NODE_URL')
    if not ethurl:
        raise Exception("requires 'ETHEREUM_NODE_URL' environment variable to be set")
    return ethurl

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

    def __init__(self, name, contract, *, from_key=None, constant=None, return_raw_tx=False):
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
            self.from_key = None
            self.from_address = None
        self.return_raw_tx = return_raw_tx

    def set_sender(self, key):
        return self.__class__(self.name, self.contract, from_key=key, constant=self.is_constant, return_raw_tx=self.return_raw_tx)

    @property
    def get_raw_tx(self):
        return self.__class__(self.name, self.contract, from_key=self.from_key, constant=self.is_constant, return_raw_tx=True)

    async def __call__(self, *args, startgas=None, gasprice=20000000000, value=0, wait_for_confirmation=True):

        # TODO: figure out if we can validate args
        validated_args = []
        for (type, name), arg in zip(self.contract.translator.function_data[self.name]['signature'], args):
            if type == 'address' and isinstance(arg, str):
                validated_args.append(data_decoder(arg))
            elif (type.startswith("uint") or type.startswith("int")) and isinstance(arg, str):
                validated_args.append(int(arg, 16))
            else:
                validated_args.append(arg)

        ethurl = get_url()

        ethclient = JsonRPCClient(ethurl)

        data = self.contract.translator.encode_function_call(self.name, validated_args)

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

            if startgas is None:
                startgas = await ethclient.eth_estimateGas(self.from_address, self.contract.address, data=data,
                                                           nonce=nonce, value=value, gasprice=gasprice)
            if startgas == 50000000 or startgas is None:
                raise Exception("Unable to estimate gas cost, possibly something wrong with the transaction arguments")

            if balance < (startgas * gasprice):
                raise Exception("Given account doesn't have enough funds")

            tx = Transaction(nonce, gasprice, startgas, self.contract.address, value, data, 0, 0, 0)
            tx.sign(self.from_key)

            tx_encoded = data_encoder(rlp.encode(tx, Transaction))

            if self.return_raw_tx:
                return tx_encoded

            try:
                tx_hash = await ethclient.eth_sendRawTransaction(tx_encoded)
            except:
                print(balance, startgas * gasprice, startgas)
                raise

            # wait for the contract to be deployed
            if wait_for_confirmation:
                print("waiting on transaction: {}".format(tx_hash))
                starttime = time.time()
                warnlevel = 0
            while wait_for_confirmation:
                resp = await ethclient.eth_getTransactionByHash(tx_hash)
                if resp is None or resp['blockNumber'] is None:
                    await asyncio.sleep(0.1)
                    if resp is None and warnlevel == 0 and time.time() - starttime < 10:
                        print("WARNING: 10 seconds have passed and transaction is not showing as a pending transaction")
                        warnlevel = 1
                    elif resp is None and warnlevel == 1 and time.time() - starttime < 60:
                        print("WARNING: 60 seconds have passed and transaction is not showing as a pending transaction")
                        raise Exception("Unexpected error waiting for transaction to complete")
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
            ethurl = get_url()

            if address is None and deployer_private_key is None:
                raise TypeError("requires either address or deployer_private_key")
            if address is None and not isinstance(constructor_data, (list, type(None))):
                raise TypeError("must supply constructor_data as a list (hint: use [] if args should be empty)")

        args = ['solc', '--combined-json', 'bin,abi']
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
