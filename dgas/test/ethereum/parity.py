import asyncio
import binascii
import bitcoin
import os
import tornado.httpclient
import tornado.escape
import signal
import subprocess
import re

from testing.common.database import (
    Database, DatabaseFactory, get_path_of, get_unused_port
)
from string import Template

from .faucet import FAUCET_PRIVATE_KEY, FAUCET_ADDRESS

from .ethminer import EthMiner

# https://github.com/ethcore/parity/wiki/Chain-specification
chaintemplate = Template("""{
    "name": "Dev",
    "engine": {
        "Ethash": {
            "params": {
                "gasLimitBoundDivisor": "0x0400",
                "minimumDifficulty": "$difficulty",
                "difficultyBoundDivisor": "0x0800",
                "durationLimit": "0x0a",
                "blockReward": "0x4563918244F40000",
                "registrar": "",
                "homesteadTransition": "0x0"
            }
        }
    },
    "params": {
        "accountStartNonce": "0x0100000",
        "maximumExtraDataSize": "0x20",
        "minGasLimit": "0x1388",
        "networkID" : "0x42"
    },
    "genesis": {
        "seal": {
            "ethereum": {
                "nonce": "0x00006d6f7264656e",
                "mixHash": "0x00000000000000000000000000000000000000647572616c65787365646c6578"
            }
        },
        "difficulty": "$difficulty",
        "author": "0x0000000000000000000000000000000000000000",
        "timestamp": "0x00",
        "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "extraData": "0x",
        "gasLimit": "0x2fefd8"
    },
    "accounts": {
        "0000000000000000000000000000000000000001": { "balance": "1", "nonce": "1048576", "builtin": { "name": "ecrecover", "pricing": { "linear": { "base": 3000, "word": 0 } } } },
        "0000000000000000000000000000000000000002": { "balance": "1", "nonce": "1048576", "builtin": { "name": "sha256", "pricing": { "linear": { "base": 60, "word": 12 } } } },
        "0000000000000000000000000000000000000003": { "balance": "1", "nonce": "1048576", "builtin": { "name": "ripemd160", "pricing": { "linear": { "base": 600, "word": 120 } } } },
        "0000000000000000000000000000000000000004": { "balance": "1", "nonce": "1048576", "builtin": { "name": "identity", "pricing": { "linear": { "base": 15, "word": 3 } } } },
        "$faucet": { "balance": "1606938044258990275541962092341162602522202993782792835301376", "nonce": "1048576" }
    }
}""")

def write_chain_file(version, fn, faucet, difficulty):

    if faucet.startswith('0x'):
        faucet = faucet[2:]

    if isinstance(difficulty, int):
        difficulty = hex(difficulty)
    elif isinstance(difficulty, str):
        if not difficulty.startswith("0x"):
            difficulty = "0x{}".format(difficulty)

    with open(fn, 'w') as f:
        f.write(chaintemplate.substitute(faucet=faucet, difficulty=difficulty))

class ParityServer(Database):

    DEFAULT_SETTINGS = dict(auto_start=2,
                            base_dir=None,
                            parity_server=None,
                            author="0x0102030405060708090001020304050607080900",
                            faucet=FAUCET_ADDRESS,
                            port=None,
                            rpcport=None,
                            bootnodes=None,
                            node_key=None,
                            no_dapps=False,
                            dapps_port=None,
                            difficulty=None,
                            copy_data_from=None)

    subdirectories = ['data', 'tmp']

    def initialize(self):
        self.parity_server = self.settings.get('parity_server')
        if self.parity_server is None:
            self.parity_server = get_path_of('parity')

        p = subprocess.Popen([self.parity_server, '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)

        for line in errs.split(b'\n') + outs.split(b'\n'):
            m = re.match("^\s+version\sParity\/v([0-9.]+).*$", line.decode('utf-8'))
            if m:
                v = tuple(int(i) for i in m.group(1).split('.'))
                break
        else:
            raise Exception("Unable to figure out Parity version")

        self.version = v
        self.chainfile = os.path.join(self.base_dir, 'chain.json')
        self.faucet = self.settings.get('faucet')

        self.author = self.settings.get('author')

        self.difficulty = self.settings.get('difficulty')
        if self.difficulty is None:
            self.difficulty = 1024

    def dsn(self, **kwargs):
        return {'node': 'enode://{}@127.0.0.1:{}'.format(self.public_key, self.settings['port']),
                'url': "http://localhost:{}/".format(self.settings['rpcport']),
                'network_id': "66"}

    def get_data_directory(self):
        return os.path.join(self.base_dir, 'data')

    def prestart(self):
        super(ParityServer, self).prestart()

        if self.settings['rpcport'] is None:
            self.settings['rpcport'] = get_unused_port()

        if self.settings['no_dapps'] is False and self.settings['dapps_port'] is None:
            self.settings['dapps_port'] = get_unused_port()

        if self.settings['node_key'] is None:
            self.settings['node_key'] = "{:0>64}".format(binascii.b2a_hex(os.urandom(32)).decode('ascii'))

        self.public_key = "{:0>128}".format(binascii.b2a_hex(bitcoin.privtopub(binascii.a2b_hex(self.settings['node_key']))[1:]).decode('ascii'))

        # write chain file
        write_chain_file(self.version, self.chainfile, self.faucet, self.difficulty)

    def get_server_commandline(self):
        if self.author.startswith("0x"):
            author = self.author[2:]
        else:
            author = self.author

        cmd = [self.parity_server,
               "--no-ui",
               "--port", str(self.settings['port']),
               "--rpcport", str(self.settings['rpcport']),
               "--datadir", self.get_data_directory(),
               "--no-color",
               "--chain", self.chainfile,
               "--author", author,
               "--tracing", 'on',
               "--node-key", self.settings['node_key']]

        if self.settings['no_dapps']:
            cmd.extend(['--no-dapps'])
        else:
            cmd.extend(['--dapps-port', str(self.settings['dapps_port'])])

        if self.settings['bootnodes'] is not None:
            if isinstance(self.settings['bootnodes'], list):
                self.settings['bootnodes'] = ','.join(self.settings['bootnodes'])

            cmd.extend(['--bootnodes', self.settings['bootnodes']])

        return cmd

    def is_server_available(self):
        try:
            tornado.httpclient.HTTPClient().fetch(
                self.dsn()['url'],
                method="POST",
                headers={'Content-Type': "application/json"},
                body=tornado.escape.json_encode({
                    "jsonrpc": "2.0",
                    "id": "1234",
                    "method": "POST",
                    "params": ["0x{}".format(self.author), "latest"]
                })
            )
            return True
        except:
            return False

    def pause(self):
        """stops service, without calling the cleanup"""
        self.terminate(signal.SIGTERM)


class ParityServerFactory(DatabaseFactory):
    target_class = ParityServer

def requires_parity(func=None, difficulty=None, pass_args=False, pass_parity=False, pass_ethminer=False, debug_ethminer=False):
    """Used to ensure all database connections are returned to the pool
    before finishing the test"""

    def wrap(fn):

        async def wrapper(self, *args, **kwargs):

            parity = ParityServer(difficulty=difficulty)
            ethminer = EthMiner(jsonrpc_url=parity.dsn()['url'],
                                debug=debug_ethminer)

            self._app.config['ethereum'] = parity.dsn()

            if pass_args:
                kwargs['parity'] = parity
                kwargs['ethminer'] = ethminer
            if pass_ethminer:
                if pass_ethminer is True:
                    kwargs['ethminer'] = ethminer
                else:
                    kwargs[pass_ethminer] = ethminer
            if pass_parity:
                if pass_parity is True:
                    kwargs['parity'] = parity
                else:
                    kwargs[pass_parity] = parity

            try:
                f = fn(self, *args, **kwargs)
                if asyncio.iscoroutine(f):
                    await f
            finally:
                ethminer.stop()
                parity.stop()

        return wrapper

    if func is not None:
        return wrap(func)
    else:
        return wrap
