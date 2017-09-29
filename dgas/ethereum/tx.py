import rlp
from ethereum.transactions import Transaction, UnsignedTransaction
from ethereum.utils import (
    big_endian_to_int, int_to_big_endian, safe_ord, sha3
)

from .utils import data_decoder, data_encoder

# TODO: do these make sense? (they were taken from geth, so i hope so!)
DEFAULT_STARTGAS = 21000
DEFAULT_GASPRICE = 4000000000

def address_decoder(data):
    """Decode an address from hex with 0x prefix to 20 bytes."""
    addr = data_decoder(data)
    if len(addr) not in (20, 0):
        raise Exception('Addresses must be 20 or 0 bytes long')
    return addr

def create_transaction(*, nonce, gasprice, startgas, to, value, data=b'', v=None, r=None, s=None, network_id=None):

    if to:
        to = address_decoder(to)
    else:
        to = b''

    if network_id is not None:
        if r is not None or s is not None:
            raise Exception("cannot set network id at the same time as r and s values")
        v = network_id

    tx = Transaction(nonce, gasprice, startgas, to, value, data, v or 0, r or 0, s or 0)
    tx._sender = None

    return tx

def is_transaction_signed(tx):
    # TODO: is there a better way to know if it's signed or not?
    if not hasattr(tx, 'v'):
        return False
    # NOTE: v can be non zero if a network id is present
    return not (tx.r == 0 and tx.s == 0)

def encode_transaction(tx):
    # if there is no network id and the tx is unsigned
    if not hasattr(tx, 'v') or (hasattr(tx, 'v') and tx.v == 0 and tx.r == 0 and tx.s == 0):
        cls = UnsignedTransaction
    else:
        cls = Transaction

    return data_encoder(rlp.encode(tx, cls))

def decode_transaction(tx):

    # make sure tx is a byte string
    if isinstance(tx, str):
        tx = data_decoder(tx)

    try:
        tx = rlp.decode(tx, Transaction)
    except rlp.exceptions.ObjectDeserializationError:
        tx = rlp.decode(tx, UnsignedTransaction)

    tx.make_mutable()

    return tx

def sign_transaction(tx, key, network_id=None):

    return_type = None
    if isinstance(tx, str):
        return_type = str
        tx = data_decoder(tx)
    if isinstance(tx, bytes):
        return_type = bytes if return_type is None else return_type
        tx = decode_transaction(tx)
    if not isinstance(tx, (Transaction, UnsignedTransaction)):
        raise Exception("Expected Transaction object or rlp encoded string representing a Transaction")

    if isinstance(key, str):
        key = data_decoder(key)

    if network_id is None and hasattr(tx, 'v'):
        # see if there is a network_id in the tx
        if tx.r == 0 and tx.s == 0 and tx.v != 0:
            network_id = tx.network_id

    tx.sign(key, network_id=network_id)
    tx._cached_rlp = None

    if return_type == str:
        return encode_transaction(tx)
    elif return_type == bytes:
        return data_decoder(encode_transaction(tx))
    else:
        return tx

def signature_from_transaction(tx):

    if isinstance(tx, str):
        tx = decode_transaction(tx)

    p1 = int_to_big_endian(tx.r)
    p2 = int_to_big_endian(tx.s)

    # make sure each string is 32 bytes long, padding with 0 when it's not
    if len(p1) < 32:
        p1 = bytes([0] * (32 - len(p1))) + p1
    if len(p2) < 32:
        p2 = bytes([0] * (32 - len(p2))) + p2

    if tx.v >= 37:
        vee = tx.v - tx.network_id * 2 - 8
    else:
        vee = tx.v

    signature = p1 + p2 + bytes([vee - 27])
    return signature

def add_signature_to_transaction(tx, signature):

    if isinstance(tx, str):
        tx = decode_transaction(tx)
        encode_at_end = True
    else:
        encode_at_end = False

    if isinstance(signature, str):
        signature = data_decoder(signature)

    if hasattr(tx, 'v') and tx.network_id is not None:
        if tx.r == 0 and tx.s == 0:
            vee = 35 + tx.network_id * 2
        else:
            raise Exception("transaction is already signed")
    else:
        vee = 27

    tx.v = safe_ord(signature[64]) + vee
    tx.r = big_endian_to_int(signature[0:32])
    tx.s = big_endian_to_int(signature[32:64])
    if tx._cached_rlp:
        tx._cached_rlp = None

    if encode_at_end:
        return encode_transaction(tx)
    return tx

def calculate_transaction_hash(tx):
    """Needed to ensure signed transactions that are born from `UnsignedTransaction`
    rlp objects include the signed portion"""

    if isinstance(tx, str):
        tx = decode_transaction(tx)

    if not hasattr(tx, 'v') or (hasattr(tx, 'v') and tx.v == 0 and tx.r == 0 and tx.s == 0):
        cls = UnsignedTransaction
    else:
        cls = Transaction

    return data_encoder(sha3(rlp.encode(tx, cls)))

def transaction_to_json(tx):
    """returns json for the given transaction in the same format as the JSONRPC responses"""

    if isinstance(tx, str):
        tx = decode_transaction(tx)

    return {
        "blockHash": None,
        "creates": None,  # TODO
        "hash": calculate_transaction_hash(tx),
        "nonce": hex(tx.nonce),
        "gas": hex(tx.startgas),
        "transactionIndex": None,
        "input": data_encoder(tx.data),
        "publicKey": None,
        "networkId": None,
        "to": data_encoder(tx.to),
        "condition": None,
        "raw": encode_transaction(tx),
        "s": hex(tx.s),
        "standardV": "0x1",  # TODO
        "r": hex(tx.r),
        "blockNumber": None,
        "v": hex(tx.v),
        "from": data_encoder(tx.sender),
        "value": hex(tx.value),
        "gasPrice": hex(tx.gasprice)
    }
