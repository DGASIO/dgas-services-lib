import unittest
from dgas.ethereum.tx import (
    add_signature_to_transaction, encode_transaction, decode_transaction,
    DEFAULT_STARTGAS, DEFAULT_GASPRICE, create_transaction,
    is_transaction_signed
)
from dgas.ethereum.utils import data_decoder, data_encoder
from ethereum.transactions import Transaction, UnsignedTransaction
import rlp

class TestTransactionUtils(unittest.TestCase):

    def test_add_signature_to_transaction(self):

        tx = "0xe9808504a817c80082520894db089a4f9a8c5f17040b4fc51647e942b5fc601d880de0b6b3a764000080"
        sig = "0xf5a43adea07d366ae420a5c75a5cae6c60d3e4aaa0b72c2f37fc387efd43d7fd30c4327f2dbd959f654857f58912129b09763329459d08e25547d895ae90fa0f01"

        expected_signed_tx = "0xf86c808504a817c80082520894db089a4f9a8c5f17040b4fc51647e942b5fc601d880de0b6b3a7640000801ca0f5a43adea07d366ae420a5c75a5cae6c60d3e4aaa0b72c2f37fc387efd43d7fda030c4327f2dbd959f654857f58912129b09763329459d08e25547d895ae90fa0f"

        signed_tx = add_signature_to_transaction(tx, sig)

        self.assertEqual(signed_tx, expected_signed_tx)

        tx_obj = decode_transaction(tx)

        add_signature_to_transaction(tx_obj, sig)

        self.assertEqual(encode_transaction(tx_obj), expected_signed_tx)

    def test_encode_decode_transaction(self):

        sender_private_key = "0x0164f7c7399f4bb1eafeaae699ebbb12050bc6a50b2836b9ca766068a9d000c0"
        sender_address = "0xde3d2d9dd52ea80f7799ef4791063a5458d13913"
        to_address = "0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"
        value = 10000000000
        nonce = 1048576
        data = b''
        gasprice = 20000000000
        startgas = DEFAULT_STARTGAS
        expected_tx_hash = "0x2f321aa116146a9bc62b61c76508295f708f42d56340c9e613ebfc27e33f240c"

        tx1 = Transaction(nonce, gasprice, startgas, to_address, value, data)
        tx1.sign(data_decoder(sender_private_key))

        self.assertEqual(data_encoder(tx1.hash), expected_tx_hash)

        # rlputx1 = rlp.encode(tx1, UnsignedTransaction)
        # rlpstx1 = rlp.encode(tx1, Transaction)

        tx1 = Transaction(nonce, gasprice, startgas, to_address, value, data)
        enc1 = rlp.encode(tx1, UnsignedTransaction)

        tx2 = rlp.decode(enc1, UnsignedTransaction)
        tx2.sign(data_decoder(sender_private_key))
        tx3 = Transaction(tx2.nonce, tx2.gasprice, tx2.startgas, tx2.to, tx2.value, tx2.data)
        tx3.sign(data_decoder(sender_private_key))

        self.assertEqual(data_encoder(tx3.sender), sender_address)
        self.assertEqual(data_encoder(tx3.hash), expected_tx_hash)
        self.assertEqual(data_encoder(tx2.sender), sender_address)
        # NOTE: this is false because tx2 still thinks it's an unsigned tx
        # so it doesn't include the signature variables in the tx
        # if this suddenly starts failing, it means the behaviour
        # has been modified in the library
        self.assertNotEqual(data_encoder(tx2.hash), expected_tx_hash)
