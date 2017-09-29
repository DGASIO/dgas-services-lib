import binascii
import regex
from ..jsonrpc.client import JsonRPCClient
from secp256k1 import PrivateKey, PublicKey, ALL_FLAGS
from ethereum.utils import bytearray_to_bytestr, sha3, safe_ord, big_endian_to_int, int_to_32bytearray, zpad
from ethereum.abi import event_id, process_type, _canonical_type, decode_abi
from ..utils import validate_hex_string

def data_decoder(data):
    """Decode `data` representing unformatted data."""
    if not data.startswith('0x'):
        data = '0x' + data

    if len(data) % 2 != 0:
        data = '0x0' + data[2:]

    return binascii.unhexlify(data[2:])

def data_encoder(data, length=None):
    """Encode unformatted binary `data`.

    If `length` is given, the result will be padded like this: ``data_encoder('\xff', 3) ==
    '0x0000ff'``.
    """
    s = binascii.hexlify(data).decode('ascii')
    if length is None:
        return '0x' + s
    else:
        return '0x' + s.rjust(length * 2, '0')

def private_key_to_address(private_key):
    """Extracts the address from the given private key, returning the
    hex representation of the address"""

    if isinstance(private_key, str):
        private_key = data_decoder(private_key)

    return data_encoder(sha3(PrivateKey(private_key).pubkey.serialize(False)[1:])[12:])


def prepare_ethereum_jsonrpc_client(config):
    if 'url' in config:
        url = config['url']
    elif 'host' in config:
        ssl = config.get('ssl', 'false')
        if ssl is True or (isinstance(ssl, str) and ssl.lower() == 'true'):
            protocol = 'https://'
        else:
            protocol = 'http://'
        port = config.get('port', '8545')
        host = config.get('host', 'localhost')
        path = config.get('path', '/')
        if not path.startswith('/'):
            path = "/{}".format(path)

        url = "{}{}:{}{}".format(protocol, host, port, path)
    return JsonRPCClient(url)

def ecrecover(msg, signature, address=None):
    """
    Returns None on failure, returns the recovered address on success.
    If address is provided: Returns True if the recovered address matches it,
    otherwise False.
    """
    rawhash = sha3(msg)

    if len(signature) >= 65:
        v = safe_ord(signature[64]) + 27
        r = big_endian_to_int(signature[0:32])
        s = big_endian_to_int(signature[32:64])
    else:
        if address:
            return False
        else:
            return None

    pk = PublicKey(flags=ALL_FLAGS)
    pk.public_key = pk.ecdsa_recover(
        rawhash,
        pk.ecdsa_recoverable_deserialize(
            zpad(bytearray_to_bytestr(int_to_32bytearray(r)), 32) +
            zpad(bytearray_to_bytestr(int_to_32bytearray(s)), 32),
            v - 27
        ),
        raw=True
    )
    pub = pk.serialize(compressed=False)

    recaddr = data_encoder(sha3(pub[1:])[-20:])
    if address:
        if not address.startswith("0x"):
            recaddr = recaddr[2:]

        return recaddr == address

    return recaddr

def sign_payload(private_key, payload):

    if isinstance(private_key, str):
        private_key = data_decoder(private_key)

    rawhash = sha3(payload)

    pk = PrivateKey(private_key, raw=True)
    signature = pk.ecdsa_recoverable_serialize(
        pk.ecdsa_sign_recoverable(rawhash, raw=True)
    )
    signature = signature[0] + bytearray_to_bytestr([signature[1]])

    return data_encoder(signature)

def checksum_encode_address(addr):
    if isinstance(addr, str):
        addr = data_decoder(addr)

    o = ''
    v = big_endian_to_int(sha3(addr.hex()))
    for i, c in enumerate(addr.hex()):
        if c in '0123456789':
            o += c
        else:
            o += c.upper() if (v & (2 ** (255 - 4 * i))) else c.lower()
    return '0x' + o

def checksum_validate_address(addr):
    if not isinstance(addr, str):
        raise ValueError("expected string input")

    expected_encoding = checksum_encode_address(data_decoder(addr))
    return expected_encoding == addr

def _process_topic(topic):
    start_args = topic.find("(")
    end_args = topic.find(")")
    if start_args == -1 or end_args == -1 or start_args > end_args or end_args != len(topic) - 1:
        raise ValueError("Missing event arguments `()`")
    name = topic[:start_args]
    if not regex.match("^[a-zA-Z][a-zA-Z0-9]*$", name):
        raise ValueError("Invalid event name")
    args = [arg.strip() for arg in topic[start_args + 1:end_args].split(',')]
    args = [_canonical_type(arg.split(' ')[0]) for arg in args if arg != '']
    return name, args

TYPES_RE = regex.compile("^([a-z]+\d*)((?:\[\d*\])*)?$")

def _convert_type(typ, value):
    if typ.startswith("uint") or typ.startswith("int"):
        return hex(value)
    elif typ.startswith("byte"):
        return data_encoder(value)
    else:
        return value

def _convert_array(typ, depth, array):
    if len(depth) > 1:
        return [_convert_array(typ, depth[1:], a) for a in array]
    else:
        return [_convert_type(typ, v) for v in array]

def encode_topic(topic):
    name, types = _process_topic(topic)
    for arg in types:
        try:
            process_type(arg)
        except AssertionError:
            raise ValueError("Invalid argument type")
    return hex(event_id(name, types)), "{}({})".format(name, ",".join(types))

def decode_event_data(topic, data):
    if isinstance(data, str):
        data = data_decoder(data)
    name, types = _process_topic(topic)
    decoded = decode_abi(types, data)
    arguments = []
    for typ, val in zip(types, decoded):
        m = TYPES_RE.match(typ)
        if m is None:
            continue
        atyp, arr = m.groups()
        if arr is None or arr == '':
            arguments.append(_convert_type(atyp, val))
        else:
            arguments.append(_convert_array(atyp, arr[1:-1].split(']['), val))
    return arguments
