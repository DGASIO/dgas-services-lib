import unittest

from tokenservices.request import generate_request_signature_data_string

class TestParseInt(unittest.TestCase):

    def test_generate_request_signature_data_string(self):

        string = generate_request_signature_data_string("POST", "/v1/user", 1485525507, None)

        self.assertEqual(string, b'POST\n/v1/user\n1485525507\n')

        string = generate_request_signature_data_string("PUT", "/v1/test", 1485525508, {"test": "hello"})

        self.assertEqual(string, b'PUT\n/v1/test\n1485525508\n840yvRuVNSuRydwpQ5FlCxM3nLbn0MkbPJAyWx7+QJE=')
