import json
import regex

from decimal import Decimal

QOFP_REGEX = regex.compile("^QOFP::(?P<type>[A-Za-z]+):(?P<json>.+)$")

class QofpBase:

    def __init__(self, type, **kwargs):

        self.type = type
        self._data = kwargs

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def render(self):

        return "QOFP::{type}:{json}".format(type=self.type, json=json.dumps(self._data))

    def __str__(self):

        return self.render()

class QofpPayment(QofpBase):

    def __init__(self, status=None, txHash=None, value=None, currency=None, fromAddress=None, toAddress=None, networkId=None, **kwargs):

        super().__init__("Payment", **kwargs)

        self['status'] = status
        self['txHash'] = txHash
        self['value'] = value
        self['currency'] = currency
        self['fromAddress'] = fromAddress
        self['toAddress'] = toAddress
        self['networkId'] = networkId

    def __setitem__(self, key, value):

        if key not in ('status', 'txHash', 'value', 'currency', 'tx_hash', 'hash', 'fromAddress', 'toAddress', 'networkId'):
            raise KeyError(key)
        if key == 'tx_hash' or key == 'hash':
            key = 'txHash'
        if key == 'value':
            if isinstance(value, (int, float, Decimal)):
                value = hex(value)
            elif value[:2] != "0x":
                raise ValueError("Expected number or hex string for value argument. got {}: \"{}\"".format(
                    type(value), value))

        return super().__setitem__(key, value)

    @classmethod
    def from_transaction(cls, tx, erc20=None, networkId=None):
        """converts a dictionary with transaction data as returned by a
        ethereum node into a qofp payment message"""

        if isinstance(tx, dict):
            if 'error' in tx:
                status = "error"
            elif tx['blockNumber'] is None:
                status = "unconfirmed"
            else:
                status = "confirmed"
            if erc20:
                value = erc20['value']
                to_address = erc20['to_address']
                currency = erc20['symbol']
            else:
                value = tx['value']
                to_address = tx['to']
                currency = "ETH"
            return QofpPayment(value=value, currency=currency, txHash=tx['hash'],
                               fromAddress=tx['from'], toAddress=to_address,
                               status=status, networkId=networkId)
        else:
            raise TypeError("Unable to create QOFP::Payment from type '{}'".format(type(tx)))

class QofpTokenPayment(QofpBase):

    def __init__(self, status=None, txHash=None, value=None, currency=None, fromAddress=None, toAddress=None, networkId=None, contractAddress=None, **kwargs):

        super().__init__("TokenPayment", **kwargs)

        self['status'] = status
        self['txHash'] = txHash
        self['value'] = value
        self['currency'] = currency
        self['fromAddress'] = fromAddress
        self['toAddress'] = toAddress
        self['networkId'] = networkId
        self['contractAddress'] = contractAddress

    def __setitem__(self, key, value):

        if key not in ('status', 'txHash', 'value', 'currency', 'tx_hash', 'hash', 'fromAddress', 'toAddress', 'networkId', 'contractAddress'):
            raise KeyError(key)
        if key == 'tx_hash' or key == 'hash':
            key = 'txHash'
        if key == 'value':
            if isinstance(value, (int, float, Decimal)):
                value = hex(value)
            elif value[:2] != "0x":
                raise ValueError("Expected number or hex string for value argument. got {}: \"{}\"".format(
                    type(value), value))

        return super().__setitem__(key, value)


VALID_QOFP_TYPES = ('message', 'command', 'init', 'initrequest', 'payment', 'paymentrequest', 'tokenpayment')
IMPLEMENTED_QOFP_TYPES = {
    'payment': QofpPayment,
    'tokenpayment': QofpTokenPayment
}

def parse_qofp_message(message):

    match = QOFP_REGEX.match(message)
    if not match:
        raise SyntaxError("Invalid QOFP message")
    body = match.group('json')
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        raise SyntaxError("Invalid QOFP message: body is not valid json")

    type = match.group('type').lower()
    if type not in VALID_QOFP_TYPES:
        raise SyntaxError("Invalid QOFP type")

    if type not in IMPLEMENTED_QOFP_TYPES:
        raise NotImplementedError("QOFP type '{}' has not been implemented yet".format(match.group('type')))

    try:
        return IMPLEMENTED_QOFP_TYPES[type](**body)
    except TypeError:
        raise SyntaxError("Invalid QOFP message: body contains unexpected fields")
