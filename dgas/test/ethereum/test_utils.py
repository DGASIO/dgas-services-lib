import unittest

from dgas.ethereum.utils import checksum_encode_address, checksum_validate_address

class TestAddressChecksumEncoding(unittest.TestCase):

    def test_address_checksum_encoding(self):

        valid_test_cases = [
            # etherscan
            "0x9ec3a56269E76E90b829A7567b3d353fbD328e1e",
            "0x84aE564d17cC014dE8CfFF4F03ECCDD68a6488e4",
            "0xE88bC6E7C9487F1a8c6D78F7958592fc4DcF82B9",
            "0x35Acaa89182339a2c66F281CDA02c190977AAfFf",
            "0x07470a38908C46EC5462ED59e497a3a6f5289565",
            "0x1fCAc8054aEDeCcdB6DA04AF0B5Ec54E4Cb2bFfe",
            "0x060d6B0CF61C8Ee0aD2519719a95e58372A52f8d",
            "0x4B2a7Ec2Ea26fd0650a874B87b10Be15f9b3110c",
            "0x117d988Ab63532157d47504d54ADf917F47bfed5",
            "0xFA7dE21C72b8C029DC709608F96fa3133b6D9044",
            # All caps
            "0x52908400098527886E0F7030069857D2E4169EE7",
            "0x8617E340B3D01FA5F11F306F4090FD50E238070D",
            # All lower
            "0xde709f2102306220921060314715629080e2fb77",
            "0x27b1fdb04752bbc536007a920d24acb045561c26",
            # Normal
            "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
            "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
            "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        ]

        invalid_test_cases = [
            "0xCd2a3d9f938e13Cd947eC05ABC7fe734df8DD826",
            "0x9Ca0e998dF92c5351cEcbBb6Dba82Ac2266f7e0C",
            "0xcB16D0E54450Cdd2368476E762B09D147972b637"
        ]

        for address in valid_test_cases:

            self.assertEqual(checksum_encode_address(address.lower()), address)
            self.assertTrue(checksum_validate_address(address))

        for address in invalid_test_cases:

            self.assertFalse(checksum_validate_address(address))
