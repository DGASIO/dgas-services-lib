from ..jsonrpc.client import JsonRPCClient
from secp256k1 import PrivateKey, PublicKey, ALL_FLAGS
import binascii
from ethereum.utils import bytearray_to_bytestr, sha3, safe_ord, big_endian_to_int, int_to_32bytearray, zpad

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
