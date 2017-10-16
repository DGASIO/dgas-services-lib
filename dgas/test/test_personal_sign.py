import unittest
from dgas.ethereum.utils import personal_ecrecover, data_decoder, personal_sign

TEST_PRIVATE_KEY = b'W\xe5\xa7B\x1f\x01uj!+DX_\x8b~\xd1\x7f>JN9}\x9a\x1b\xea\xd9?\x80m\xb5\x1dH'
TEST_ADDRESS = "0x22928db3e4f4dd08200e1a3d4f9bfb65296cecd1"

class TestPersonalSign(unittest.TestCase):
    def test_personal_sign(self):
        msg = "Hello world!"
        signature = personal_sign(TEST_PRIVATE_KEY, msg)
        signature_bytes = data_decoder(signature)
        self.assertTrue(signature_bytes[-1] == 27 or signature_bytes[-1] == 28, "signature must be an ethereum signature")
        self.assertEqual("0x9ab94a7f9455231eabc3d8cb4e343e87d34d820dec276f4c89c56eb4c965cc855d63c7208cd72054e6f9bf792493debf8e03a80a511d508c4c2d3f8dff05655b1b", signature)
        self.assertTrue(personal_ecrecover(msg, signature, TEST_ADDRESS))
