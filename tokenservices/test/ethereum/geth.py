import asyncio
import binascii
import bitcoin
import os
import functools
import tornado.httpclient
import tornado.escape
import subprocess
import socket
import re

from tornado.websocket import websocket_connect

from testing.common.database import (
    Database, DatabaseFactory, get_path_of, get_unused_port
)
from string import Template

from .faucet import FAUCET_PRIVATE_KEY, FAUCET_ADDRESS

chaintemplate = Template("""{
    "nonce": "0x0000000000000042",
    "timestamp": "0x0",
    "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "extraData": "0x0",
    "gasLimit": "0x8000000",
    "difficulty": "$difficulty",
    "mixhash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "coinbase": "0x3333333333333333333333333333333333333333",
    "alloc": {
        "0x$author": {
            "balance": "1606938044258990275541962092341162602522202993782792835301376"
        }
    }
}
""")

def write_chain_file(version, fn, author, difficulty):

    if author.startswith('0x'):
        author = author[2:]

    if isinstance(difficulty, int):
        difficulty = hex(difficulty)
    elif isinstance(difficulty, str):
        if not difficulty.startswith("0x"):
            difficulty = "0x{}".format(difficulty)

    with open(fn, 'w') as f:
        f.write(chaintemplate.substitute(author=author, difficulty=difficulty))

class GethServer(Database):

    DEFAULT_SETTINGS = dict(auto_start=2,
                            base_dir=None,
                            geth_server=None,
                            author=FAUCET_ADDRESS,
                            port=None,
                            rpcport=None,
                            bootnodes=None,
                            node_key=None,
                            no_dapps=False,
                            dapps_port=None,
                            ws=None,
                            difficulty=None,
                            copy_data_from=None)

    subdirectories = ['data', 'tmp']

    def initialize(self):
        self.geth_server = self.settings.get('geth_server')
        if self.geth_server is None:
            self.geth_server = get_path_of('geth')

        self.difficulty = self.settings.get('difficulty')
        if self.difficulty is None:
            self.difficulty = 1024

        p = subprocess.Popen([self.geth_server, 'version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)

        for line in outs.split(b'\n'):
            m = re.match("^Version:\s([0-9.]+)(?:-[a-z]+)?$", line.decode('utf-8'))
            if m:
                v = tuple(int(i) for i in m.group(1).split('.'))
                break
        else:
            raise Exception("Unable to figure out Geth version")

        self.version = v
        self.chainfile = os.path.join(self.base_dir, 'chain.json')
        self.author = self.settings.get('author')

    def dsn(self, **kwargs):
        dsn = {
            'node': 'enode://{}@127.0.0.1:{}'.format(self.public_key, self.settings['port']),
            'url': "http://localhost:{}/".format(self.settings['rpcport'])
        }
        if self.settings['ws'] is not None:
            dsn['ws'] = 'ws://localhost:{}'.format(self.settings['wsport'])
        return dsn

    def get_data_directory(self):
        return os.path.join(self.base_dir, 'data')

    def prestart(self):
        super().prestart()

        # geth is locked to user home
        home = os.path.expanduser("~")
        dagfile = os.path.join(home, '.ethash', 'full-R23-0000000000000000')
        if not os.path.exists(dagfile):
            raise Exception("Missing DAG {}. run {} makedag 0 {} to initialise ethminer before tests can be run".format(
                dagfile, self.geth_server, os.path.join(home, '.ethash')))

        if self.settings['rpcport'] is None:
            self.settings['rpcport'] = get_unused_port()

        if self.settings['node_key'] is None:
            self.settings['node_key'] = "{:0>64}".format(binascii.b2a_hex(os.urandom(32)).decode('ascii'))

        if self.settings['ws'] is not None:
            self.settings['wsport'] = get_unused_port()

        self.public_key = "{:0>128}".format(binascii.b2a_hex(bitcoin.privtopub(binascii.a2b_hex(self.settings['node_key']))[1:]).decode('ascii'))

        # write chain file
        write_chain_file(self.version, self.chainfile, self.author, self.difficulty)

        p = subprocess.Popen([self.geth_server, '--datadir', self.get_data_directory(), 'init', self.chainfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)

        with open(os.path.join(self.get_data_directory(), 'keystore', 'UTC--2017-02-06T16-16-34.720321115Z--de3d2d9dd52ea80f7799ef4791063a5458d13913'), 'w') as inf:
            inf.write('''{"address":"de3d2d9dd52ea80f7799ef4791063a5458d13913","crypto":{"cipher":"aes-128-ctr","ciphertext":"8d6528acfb366722d9c98f64435bb151f5671f9e4623e546cc7206382a1d54f7","cipherparams":{"iv":"de95c854face9aa50686370cc47d6025"},"kdf":"scrypt","kdfparams":{"dklen":32,"n":262144,"p":1,"r":8,"salt":"6baa74518f9cc34575c981e027154e9c714b400710478c587043c900a37a89b8"},"mac":"37b6d35ea394b129f07e9a90a09b8cc1356d731590201e84405f4592013b4333"},"id":"ce658bd4-6910-4eef-aa39-b32000c38ccc","version":3}''')

    def get_server_commandline(self):
        if self.author.startswith("0x"):
            author = self.author[2:]
        else:
            author = self.author

        cmd = [self.geth_server,
               "--port", str(self.settings['port']),
               "--rpc",
               "--rpcport", str(self.settings['rpcport']),
               "--rpcapi", "eth,web3,personal,debug,admin,miner",
               "--datadir", self.get_data_directory(),
               "--etherbase", author,
               "--mine", "--nat", "none", "--verbosity", "6",
               "--nodekeyhex", self.settings['node_key']]

        if self.settings['ws'] is not None:
            cmd.extend(['--ws', '--wsport', str(self.settings['wsport']), '--wsorigins', '*'])

        if self.settings['bootnodes'] is not None:
            if isinstance(self.settings['bootnodes'], list):
                self.settings['bootnodes'] = ','.join(self.settings['bootnodes'])

            cmd.extend(['--bootnodes', self.settings['bootnodes']])

        return cmd

    def is_server_available(self):
        try:
            if self.settings['ws'] is not None:
                ioloop = tornado.ioloop.IOLoop(make_current=False)
                ioloop.run_sync(functools.partial(
                    geth_websocket_connect, self.dsn()['ws']))
            else:
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
        except (tornado.httpclient.HTTPError,) as e:
            return False
        except (ConnectionRefusedError,) as e:
            return False

class GethServerFactory(DatabaseFactory):
    target_class = GethServer

def requires_geth(func=None, pass_server=False, **server_kwargs):
    """Used to ensure all database connections are returned to the pool
    before finishing the test"""

    def wrap(fn):

        async def wrapper(self, *args, **kwargs):

            geth = GethServer(**server_kwargs)

            self._app.config['ethereum'] = geth.dsn()

            if pass_server:
                if isinstance(pass_server, str):
                    kwargs[pass_server] = geth
                else:
                    kwargs['geth'] = geth

            try:
                f = fn(self, *args, **kwargs)
                if asyncio.iscoroutine(f):
                    await f
            finally:
                geth.stop()

        return wrapper

    if func is not None:
        return wrap(func)
    else:
        return wrap

def geth_websocket_connect(url, io_loop=None, callback=None, connect_timeout=None,
                           on_message_callback=None, compression_options=None):
    """Helper function for connecting to geth via websockets, which may need the
    origin set should there be no --wsorigin * option set in geth's config"""

    if not isinstance(url, tornado.httpclient.HTTPRequest):
        if url.startswith('wss://'):
            origin = 'https://{}'.format(socket.gethostname())
        else:
            origin = 'http://{}'.format(socket.gethostname())
        url = tornado.httpclient.HTTPRequest(url, headers={'Origin': origin})
    return websocket_connect(url, io_loop=io_loop, callback=callback, connect_timeout=connect_timeout,
                             on_message_callback=on_message_callback, compression_options=compression_options)
