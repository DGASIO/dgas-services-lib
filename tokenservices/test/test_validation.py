import unittest

from tokenservices import utils

class TestValidation(unittest.TestCase):

    def test_validate_address(self):

        self.assertTrue(utils.validate_address("0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"))
        self.assertTrue(utils.validate_address(u"0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"))
        self.assertFalse(utils.validate_address("hello"))
        self.assertFalse(utils.validate_address("0x12345"))
        self.assertFalse(utils.validate_address(None))
        self.assertFalse(utils.validate_address({}))
        self.assertFalse(utils.validate_address(0x056db290f8ba3250ca64a45d16284d04bc6f5fbf))
        self.assertFalse(utils.validate_address("0x114655db4898a6580f0abfc53fc0c0a88110724abf8d41f2abf206c69d7d4c821ed2cdf6939484ef6aebc39ce5662363b82140106bbc374a0f1381b6948214b001"))

    def test_validate_signature(self):

        self.assertTrue(utils.validate_signature("0x114655db4898a6580f0abfc53fc0c0a88110724abf8d41f2abf206c69d7d4c821ed2cdf6939484ef6aebc39ce5662363b82140106bbc374a0f1381b6948214b001"))
        self.assertTrue(utils.validate_signature(u"0x114655db4898a6580f0abfc53fc0c0a88110724abf8d41f2abf206c69d7d4c821ed2cdf6939484ef6aebc39ce5662363b82140106bbc374a0f1381b6948214b001"))
        self.assertFalse(utils.validate_signature("hello"))
        self.assertFalse(utils.validate_signature("0x12345"))
        self.assertFalse(utils.validate_signature(None))
        self.assertFalse(utils.validate_signature({}))
        self.assertFalse(utils.validate_signature(0x114655db4898a6580f0abfc53fc0c0a88110724abf8d41f2abf206c69d7d4c821ed2cdf6939484ef6aebc39ce5662363b82140106bbc374a0f1381b6948214b001))
        self.assertFalse(utils.validate_signature("0x056db290f8ba3250ca64a45d16284d04bc6f5fbf"))

    def test_validate_hex_string(self):

        self.assertTrue(utils.validate_hex_string("0x1"))
        self.assertTrue(utils.validate_hex_string(u"0x1"))
        self.assertTrue(utils.validate_hex_string("0xA"))
        self.assertTrue(utils.validate_hex_string("0xABCDEF"))
        self.assertFalse(utils.validate_hex_string("0xHIJKL"))
        self.assertFalse(utils.validate_hex_string(12345))
        self.assertFalse(utils.validate_hex_string(0xABC))
        self.assertFalse(utils.validate_hex_string(None))
        self.assertFalse(utils.validate_hex_string({}))
        self.assertFalse(utils.validate_hex_string("ABCDEF"))
        self.assertFalse(utils.validate_hex_string("0x"))

    def test_validate_int_string(self):

        self.assertTrue(utils.validate_int_string("12345"))
        self.assertTrue(utils.validate_int_string(u"12345"))
        self.assertTrue(utils.validate_int_string("1"))
        self.assertTrue(utils.validate_int_string("-1"))
        self.assertTrue(utils.validate_int_string("2000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001"))
        self.assertFalse(utils.validate_int_string("1.2"))
        self.assertFalse(utils.validate_int_string("0xABC"))
        self.assertFalse(utils.validate_int_string(0xABC))
        self.assertFalse(utils.validate_int_string(None))
        self.assertFalse(utils.validate_int_string({}))
        self.assertFalse(utils.validate_int_string("ABCDEF"))
        self.assertFalse(utils.validate_int_string("01"))

    def test_validate_decimal_string(self):

        self.assertTrue(utils.validate_decimal_string("12345.0000"))
        self.assertTrue(utils.validate_decimal_string(u"12345.0000"))
        self.assertTrue(utils.validate_decimal_string("12345.12345"))
        self.assertTrue(utils.validate_decimal_string("-1.2"))
        self.assertTrue(utils.validate_decimal_string("1.0"))
        self.assertTrue(utils.validate_decimal_string("2.000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001"))
        self.assertFalse(utils.validate_decimal_string("1"))
        self.assertFalse(utils.validate_decimal_string("0xABC"))
        self.assertFalse(utils.validate_decimal_string(0xABC))
        self.assertFalse(utils.validate_decimal_string(None))
        self.assertFalse(utils.validate_decimal_string({}))
        self.assertFalse(utils.validate_decimal_string("ABCDEF"))
        self.assertFalse(utils.validate_decimal_string("01.1"))
