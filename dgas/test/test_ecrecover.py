import unittest
from dgas.ethereum.utils import ecrecover, data_decoder

class TestEcrecover(unittest.TestCase):
    def test_valid_recovery(self):
        self.assertTrue(ecrecover(
            '{"custom":{"about":"about ","location":"location "},"timestamp":1483968938,"username":"Colin"}',
            data_decoder('0xbd5c9009cc87c6d4ebb3ef8223fc036726bc311678890890619c787aa914d3b636aee82d885c6fb668233b5cc70ab09eea7051648f989e758ee09234f5340d9100'),
            '0x5249dc212cd9c16f107c50b6c893952d617c011e'
        ))

    def test_valid_recovery_unicode(self):
        self.assertTrue(ecrecover(
            '{"custom":{"about":"æ","location":""},"timestamp":1483964545,"username":"Col"}',
            data_decoder('0xb3c61812e1e73f1a75cc9a2f5e748099378b7af2dd8bc3c1b4f0c067e6e9a4012d0c411b77bab63708b350742d41de574add6b06a3d06a5ae10fc9c63c18405301'),
            '0x5249dc212cd9c16f107c50b6c893952d617c011e'
        ))

    def test_too_short_signature(self):
        self.assertEqual(ecrecover(
            '{"custom":{"about":"æ","location":""},"timestamp":1483964545,"username":"Col"}',
            data_decoder('0x5301')
        ), None)

    def test_too_short_signature_comparison(self):
        self.assertFalse(ecrecover(
            '{"custom":{"about":"æ","location":""},"timestamp":1483964545,"username":"Col"}',
            data_decoder('0x5301'),
            '0x5249dc212cd9c16f107c50b6c893952d617c011e'
        ))
