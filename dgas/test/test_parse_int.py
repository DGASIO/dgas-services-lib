import unittest

from decimal import Decimal
from dgas.utils import parse_int

class TestParseInt(unittest.TestCase):

    def test_parse_int_string(self):

        self.assertEqual(parse_int("12345"), 12345)

    def test_parse_negative_int_string(self):

        self.assertEqual(parse_int("-12345"), -12345)

    def test_parse_zero_int_string(self):

        self.assertEqual(parse_int("0"), 0)

    def test_parse_int_no_leading_zeros_string(self):

        self.assertEqual(parse_int("0123"), None)

    def test_parse_float_string(self):

        self.assertEqual(parse_int("12345.567678"), 12345)

    def test_parse_hex_string(self):

        self.assertEqual(parse_int("0x12345"), 74565)

    def test_parse_float(self):

        self.assertEqual(parse_int(12345.45675), 12345)

    def test_parse_decimal(self):

        self.assertEqual(parse_int(Decimal("12345.6787")), 12345)

    def test_parse_none(self):

        self.assertEqual(parse_int(None), None)

    def test_parse_misc(self):

        self.assertEqual(parse_int({}), None)

    def test_parse_bytes(self):

        self.assertEqual(parse_int(b"12345"), 12345)

    def test_parse_unicode(self):

        self.assertEqual(parse_int(u'12345'), 12345)
