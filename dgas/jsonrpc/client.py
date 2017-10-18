import asyncio
import binascii
import random
import regex
import tornado.httpclient
import logging

from .errors import JsonRPCError

JSONRPC_LOG = logging.getLogger("dgas.jsonrpc.client")

JSON_RPC_VERSION = "2.0"

HEX_RE = regex.compile("(0x)?([0-9a-fA-F]+)")

def validate_hex(value, length=None):
    if isinstance(value, int):
        value = hex(value)[2:]
    if isinstance(value, bytes):
        value = binascii.b2a_hex(value).decode('ascii')
    else:
        m = HEX_RE.match(value)
        if m:
            value = m.group(2)
        else:
            raise ValueError("Unable to convert value to valid hex string")
    if length:
        if len(value) > length * 2:
            raise ValueError("Value is too long")
        return '0x' + value.rjust(length * 2, '0')
    return '0x' + value

def validate_block_param(param):

    if param not in ("earliest", "latest", "pending"):
        return validate_hex(param)
    return param

class JsonRPCClient:

    def __init__(self, url, should_retry=True, log=None):
        self._url = url
        self._httpclient = tornado.httpclient.AsyncHTTPClient()
        if log is None:
            self.log = JSONRPC_LOG
        else:
            self.log = log
        self.should_retry = should_retry

    async def _fetch(self, method, params=None):
        id = random.randint(0, 1000000)

        if params is None:
            params = []

        data = {
            "jsonrpc": JSON_RPC_VERSION,
            "id": id,
            "method": method,
            "params": params
        }

        # NOTE: letting errors fall through here for now as it means
        # there is something drastically wrong with the jsonrpc server
        # which means something probably needs to be fixed
        retries = 0
        while True:
            try:
                resp = await self._httpclient.fetch(
                    self._url,
                    method="POST",
                    headers={'Content-Type': "application/json"},
                    body=tornado.escape.json_encode(data)
                )
            except:
                self.log.error("Error in JsonRPCClient._fetch ({}): retry {}".format(method, retries))
                retries += 1
                # give up after a "while"
                if not self.should_retry or retries >= 5:
                    raise
                await asyncio.sleep(0.5)
            else:
                break

        rval = tornado.escape.json_decode(resp.body)

        # verify the id we got back is the same as what we passed
        if id != rval['id']:
            raise JsonRPCError(-1, "returned id was not the same as the inital request")

        if "error" in rval:
            # monitor if errors with block number happen often
            if "Unknown block number" in rval['error']['message']:
                self.log.error("Got 'Unknown block number' when calling '{}' with params: {}".format(method, params))
            raise JsonRPCError(rval['id'], rval['error']['code'], rval['error']['message'], rval['error']['data'] if 'data' in rval['error'] else None)

        return rval['result']

    async def eth_getBalance(self, address, block="latest"):

        address = validate_hex(address)
        block = validate_block_param(block)

        result = await self._fetch("eth_getBalance", [address, block])

        if result.startswith("0x"):
            result = result[2:]

        return int(result, 16)

    async def eth_getTransactionCount(self, address, block="latest"):

        address = validate_hex(address)
        block = validate_block_param(block)

        result = await self._fetch("eth_getTransactionCount", [address, block])

        if result.startswith("0x"):
            result = result[2:]

        return int(result, 16)

    async def eth_estimateGas(self, source_address, target_address, **kwargs):

        source_address = validate_hex(source_address)
        hexkwargs = {"from": source_address}

        if target_address:
            target_address = validate_hex(target_address)
            hexkwargs["to"] = target_address

        for k, value in kwargs.items():
            if k == 'gasprice' or k == 'gas_price':
                k = 'gasPrice'
            hexkwargs[k] = validate_hex(value)
        if 'value' not in hexkwargs:
            hexkwargs['value'] = "0x0"
        result = await self._fetch("eth_estimateGas", [hexkwargs])

        return int(result, 16)

    async def eth_sendRawTransaction(self, tx):

        tx = validate_hex(tx)
        result = await self._fetch("eth_sendRawTransaction", [tx])

        return result

    async def eth_getTransactionReceipt(self, tx):

        tx = validate_hex(tx)
        result = await self._fetch("eth_getTransactionReceipt", [tx])

        return result

    async def eth_getTransactionByHash(self, tx):

        tx = validate_hex(tx)
        result = await self._fetch("eth_getTransactionByHash", [tx])

        return result

    async def eth_blockNumber(self):

        result = await self._fetch("eth_blockNumber", [])

        if result.startswith("0x"):
            result = result[2:]

        return int(result, 16)

    async def eth_getBlockByNumber(self, number, with_transactions=True):

        number = validate_block_param(number)

        result = await self._fetch("eth_getBlockByNumber", [number, with_transactions])

        return result

    async def eth_newFilter(self, *, fromBlock=None, toBlock=None, address=None, topics=None):

        kwargs = {}
        if fromBlock:
            kwargs['fromBlock'] = validate_block_param(fromBlock)
        if toBlock:
            kwargs['toBlock'] = validate_block_param(toBlock)
        if address:
            kwargs['address'] = validate_hex(address)
        if topics:
            if not isinstance(topics, list):
                raise TypeError("topics must be an array of DATA")
            kwargs['topics'] = [None if i is None else validate_hex(i, 32) for i in topics]

        result = await self._fetch("eth_newFilter", [kwargs])

        return result

    async def eth_newPendingTransactionFilter(self):

        result = await self._fetch("eth_newPendingTransactionFilter", [])

        return result

    async def eth_newBlockFilter(self):

        result = await self._fetch("eth_newBlockFilter", [])

        return result

    async def eth_getFilterChanges(self, filter_id):

        result = await self._fetch("eth_getFilterChanges", [filter_id])

        return result

    async def eth_getFilterLogs(self, filter_id):

        result = await self._fetch("eth_getFilterLogs", [filter_id])

        return result

    async def eth_uninstallFilter(self, filter_id):

        result = await self._fetch("eth_uninstallFilter", [filter_id])

        return result

    async def eth_getCode(self, address, block="latest"):

        address = validate_hex(address)
        block = validate_block_param(block)
        result = await self._fetch("eth_getCode", [address, block])

        return result

    async def eth_getLogs(self, fromBlock=None, toBlock=None, address=None, topics=None):

        kwargs = {}
        if fromBlock:
            kwargs['fromBlock'] = validate_block_param(fromBlock)
        if toBlock:
            kwargs['toBlock'] = validate_block_param(toBlock)
        if address:
            kwargs['address'] = validate_hex(address)
        if topics:
            # validate topics
            if not isinstance(topics, list):
                raise TypeError("topics must be an array of DATA")
            for topic in topics:
                if isinstance(topic, list):
                    if not all(validate_hex(t, 32) for t in topic):
                        raise TypeError("topics must be an array of DATA")
                else:
                    if not validate_hex(topic):
                        raise TypeError("topics must be an array of DATA")
            kwargs['topics'] = topics

        result = await self._fetch("eth_getLogs", [kwargs])

        return result

    async def eth_call(self, *, to_address, from_address=None, gas=None, gasprice=None, value=None, data=None, block="latest"):

        to_address = validate_hex(to_address)
        block = validate_block_param(block)

        callobj = {"to": to_address}
        if from_address:
            callobj['from'] = validate_hex(from_address)
        if gas:
            callobj['gas'] = validate_hex(gas)
        if gasprice:
            callobj['gasPrice'] = validate_hex(gasprice)
        if value:
            callobj['value'] = validate_hex(value)
        if data:
            callobj['data'] = validate_hex(data)

        result = await self._fetch("eth_call", [callobj, block])
        return result

    async def trace_transaction(self, transaction_hash):

        result = await self._fetch("trace_transaction", [transaction_hash])

        return result

    async def trace_get(self, transaction_hash, *positions):

        result = await self._fetch("trace_get", [transaction_hash, positions])
        return result

    async def trace_replayTransaction(self, transaction_hash, *, vmTrace=False, trace=True, stateDiff=False):

        trace_type = []
        if vmTrace:
            trace_type.append('vmTrace')
        if trace:
            trace_type.append('trace')
        if stateDiff:
            trace_type.append('stateDiff')

        result = await self._fetch("trace_replayTransaction", [transaction_hash, trace_type])

        return result

    async def debug_traceTransaction(self, transaction_hash, *, disableStorage=None, disableMemory=None, disableStack=None,
                                     fullStorage=None, tracer=None, timeout=None):
        kwargs = {}
        if disableStorage is not None:
            kwargs['disableStorage'] = disableStorage
        if disableMemory is not None:
            kwargs['disableMemory'] = disableMemory
        if disableStack is not None:
            kwargs['disableStack'] = disableStack
        if tracer is not None:
            kwargs['tracer'] = tracer
        if timeout is not None:
            kwargs['timeout'] = str(timeout)

        result = await self._fetch("debug_traceTransaction", [transaction_hash, kwargs])
        return result

    async def web3_clientVersion(self):

        result = await self._fetch("web3_clientVersion", [])
        return result

    async def net_version(self):

        return (await self._fetch("net_version", []))
