import asyncio
import binascii
import bitcoin
import os
import functools
import tornado.httpclient
import tornado.escape
import subprocess
import socket
import re

from tornado.websocket import websocket_connect

from testing.common.database import (
    Database, DatabaseFactory, get_path_of, get_unused_port
)
from string import Template

from .faucet import FAUCET_PRIVATE_KEY, FAUCET_ADDRESS

from .ethminer import EthMiner

## generated using puppeth 1.6.0
chaintemplate = Template("""
{
  "config": {
    "chainId": 66,
    "homesteadBlock": 1,
    "eip150Block": 2,
    "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "eip155Block": 3,
    "eip158Block": 3,
    "ethash": {}
  },
  "nonce": "0x0",
  "timestamp": "0x58f59ade",
  "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
  "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000",
  "gasLimit": "0x47b760",
  "difficulty": "$difficulty",
  "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
  "coinbase": "0x0000000000000000000000000000000000000000",
  "alloc": {
    "0000000000000000000000000000000000000000": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000001": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000002": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000003": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000004": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000005": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000006": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000007": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000008": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000009": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000000a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000000b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000000c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000000d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000000e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000000f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000010": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000011": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000012": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000013": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000014": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000015": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000016": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000017": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000018": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000019": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000001a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000001b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000001c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000001d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000001e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000001f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000020": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000021": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000022": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000023": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000024": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000025": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000026": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000027": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000028": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000029": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000002a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000002b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000002c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000002d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000002e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000002f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000030": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000031": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000032": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000033": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000034": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000035": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000036": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000037": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000038": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000039": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000003a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000003b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000003c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000003d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000003e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000003f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000040": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000041": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000042": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000043": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000044": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000045": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000046": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000047": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000048": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000049": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000004a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000004b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000004c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000004d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000004e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000004f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000050": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000051": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000052": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000053": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000054": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000055": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000056": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000057": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000058": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000059": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000005a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000005b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000005c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000005d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000005e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000005f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000060": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000061": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000062": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000063": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000064": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000065": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000066": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000067": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000068": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000069": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000006a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000006b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000006c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000006d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000006e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000006f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000070": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000071": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000072": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000073": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000074": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000075": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000076": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000077": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000078": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000079": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000007a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000007b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000007c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000007d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000007e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000007f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000080": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000081": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000082": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000083": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000084": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000085": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000086": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000087": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000088": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000089": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000008a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000008b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000008c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000008d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000008e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000008f": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000090": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000091": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000092": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000093": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000094": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000095": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000096": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000097": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000098": {
      "balance": "0x1"
    },
    "0000000000000000000000000000000000000099": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000009a": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000009b": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000009c": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000009d": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000009e": {
      "balance": "0x1"
    },
    "000000000000000000000000000000000000009f": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a0": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a1": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a2": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a3": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a4": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a5": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a6": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a7": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a8": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000a9": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000aa": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ab": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ac": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ad": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ae": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000af": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b0": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b1": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b2": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b3": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b4": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b5": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b6": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b7": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b8": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000b9": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ba": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000bb": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000bc": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000bd": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000be": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000bf": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c0": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c1": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c2": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c3": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c4": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c5": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c6": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c7": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c8": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000c9": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ca": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000cb": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000cc": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000cd": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ce": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000cf": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d0": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d1": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d2": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d3": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d4": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d5": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d6": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d7": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d8": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000d9": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000da": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000db": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000dc": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000dd": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000de": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000df": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e0": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e1": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e2": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e3": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e4": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e5": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e6": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e7": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e8": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000e9": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ea": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000eb": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ec": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ed": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ee": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ef": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f0": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f1": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f2": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f3": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f4": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f5": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f6": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f7": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f8": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000f9": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000fa": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000fb": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000fc": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000fd": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000fe": {
      "balance": "0x1"
    },
    "00000000000000000000000000000000000000ff": {
      "balance": "0x1"
    },
    "0x$author": {
      "balance": "0x200000000000000000000000000000000000000000000000000000000000000"
    }
  }
}
""")

def write_chain_file(version, fn, author, difficulty):

    if author.startswith('0x'):
        author = author[2:]

    if isinstance(difficulty, int):
        difficulty = hex(difficulty)
    elif isinstance(difficulty, str):
        if not difficulty.startswith("0x"):
            difficulty = "0x{}".format(difficulty)

    with open(fn, 'w') as f:
        f.write(chaintemplate.substitute(author=author, difficulty=difficulty))

class GethServer(Database):

    DEFAULT_SETTINGS = dict(auto_start=2,
                            base_dir=None,
                            geth_server=None,
                            author=FAUCET_ADDRESS,
                            port=None,
                            rpcport=None,
                            bootnodes=None,
                            node_key=None,
                            no_dapps=False,
                            dapps_port=None,
                            ws=None,
                            mine=True,
                            difficulty=None,
                            copy_data_from=None)

    subdirectories = ['data', 'tmp']

    def initialize(self):
        self.geth_server = self.settings.get('geth_server')
        if self.geth_server is None:
            self.geth_server = get_path_of('geth')

        self.difficulty = self.settings.get('difficulty')
        if self.difficulty is None:
            self.difficulty = 1024

        p = subprocess.Popen([self.geth_server, 'version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)

        for line in outs.split(b'\n'):
            m = re.match("^Version:\s([0-9.]+)(?:-[a-z]+)?$", line.decode('utf-8'))
            if m:
                v = tuple(int(i) for i in m.group(1).split('.'))
                break
        else:
            raise Exception("Unable to figure out Geth version")

        self.version = v
        self.chainfile = os.path.join(self.base_dir, 'chain.json')
        self.author = self.settings.get('author')

    def dsn(self, **kwargs):
        dsn = {
            'node': 'enode://{}@127.0.0.1:{}'.format(self.public_key, self.settings['port']),
            'url': "http://localhost:{}/".format(self.settings['rpcport']),
            'network_id': "66"
        }
        if self.settings['ws'] is not None:
            dsn['ws'] = 'ws://localhost:{}'.format(self.settings['wsport'])
        return dsn

    def get_data_directory(self):
        return os.path.join(self.base_dir, 'data')

    def prestart(self):
        super().prestart()

        # geth is locked to user home
        home = os.path.expanduser("~")
        dagfile = os.path.join(home, '.ethash', 'full-R23-0000000000000000')
        if not os.path.exists(dagfile):
            raise Exception("Missing DAG {}. run {} makedag 0 {} to initialise ethminer before tests can be run".format(
                dagfile, self.geth_server, os.path.join(home, '.ethash')))

        if self.settings['rpcport'] is None:
            self.settings['rpcport'] = get_unused_port()

        if self.settings['node_key'] is None:
            self.settings['node_key'] = "{:0>64}".format(binascii.b2a_hex(os.urandom(32)).decode('ascii'))

        if self.settings['ws'] is not None:
            self.settings['wsport'] = get_unused_port()

        self.public_key = "{:0>128}".format(binascii.b2a_hex(bitcoin.privtopub(binascii.a2b_hex(self.settings['node_key']))[1:]).decode('ascii'))

        # write chain file
        write_chain_file(self.version, self.chainfile, self.author, self.difficulty)

        p = subprocess.Popen([self.geth_server, '--datadir', self.get_data_directory(), 'init', self.chainfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outs, errs = p.communicate(timeout=15)

        with open(os.path.join(self.get_data_directory(), 'keystore', 'UTC--2017-02-06T16-16-34.720321115Z--de3d2d9dd52ea80f7799ef4791063a5458d13913'), 'w') as inf:
            inf.write('''{"address":"de3d2d9dd52ea80f7799ef4791063a5458d13913","crypto":{"cipher":"aes-128-ctr","ciphertext":"8d6528acfb366722d9c98f64435bb151f5671f9e4623e546cc7206382a1d54f7","cipherparams":{"iv":"de95c854face9aa50686370cc47d6025"},"kdf":"scrypt","kdfparams":{"dklen":32,"n":262144,"p":1,"r":8,"salt":"6baa74518f9cc34575c981e027154e9c714b400710478c587043c900a37a89b8"},"mac":"37b6d35ea394b129f07e9a90a09b8cc1356d731590201e84405f4592013b4333"},"id":"ce658bd4-6910-4eef-aa39-b32000c38ccc","version":3}''')

    def get_server_commandline(self):
        if self.author.startswith("0x"):
            author = self.author[2:]
        else:
            author = self.author

        cmd = [self.geth_server,
               "--port", str(self.settings['port']),
               "--rpc",
               "--rpcport", str(self.settings['rpcport']),
               "--rpcapi", "eth,web3,personal,debug,admin,miner",
               "--datadir", self.get_data_directory(),
               "--etherbase", author,
               "--nat", "none", "--verbosity", "6",
               "--nodekeyhex", self.settings['node_key']]

        if self.settings['mine'] is True:
            cmd.append("--mine")

        if self.settings['ws'] is not None:
            cmd.extend(['--ws', '--wsport', str(self.settings['wsport']), '--wsorigins', '*'])

        if self.settings['bootnodes'] is not None:
            if isinstance(self.settings['bootnodes'], list):
                self.settings['bootnodes'] = ','.join(self.settings['bootnodes'])

            cmd.extend(['--bootnodes', self.settings['bootnodes']])

        return cmd

    def is_server_available(self):
        try:
            if self.settings['ws'] is not None:
                ioloop = tornado.ioloop.IOLoop(make_current=False)
                ioloop.run_sync(functools.partial(
                    geth_websocket_connect, self.dsn()['ws']))
            else:
                tornado.httpclient.HTTPClient().fetch(
                    self.dsn()['url'],
                    method="POST",
                    headers={'Content-Type': "application/json"},
                    body=tornado.escape.json_encode({
                        "jsonrpc": "2.0",
                        "id": "1234",
                        "method": "POST",
                        "params": ["0x{}".format(self.author), "latest"]
                    })
                )
            return True
        except (tornado.httpclient.HTTPError,) as e:
            return False
        except (ConnectionRefusedError,) as e:
            return False

class GethServerFactory(DatabaseFactory):
    target_class = GethServer

def requires_geth(func=None, pass_server=False, pass_ethminer=False, use_ethminer=False, **server_kwargs):
    """Used to ensure all database connections are returned to the pool
    before finishing the test"""

    def wrap(fn):

        async def wrapper(self, *args, **kwargs):

            if use_ethminer:
                server_kwargs['mine'] = False

            geth = GethServer(**server_kwargs)

            if use_ethminer:
                ethminer = EthMiner(jsonrpc_url=geth.dsn()['url'],
                                    debug=False)
            else:
                ethminer = None

            self._app.config['ethereum'] = geth.dsn()

            if pass_server:
                if isinstance(pass_server, str):
                    kwargs[pass_server] = geth
                else:
                    kwargs['geth'] = geth
            if pass_ethminer:
                if pass_ethminer is True:
                    kwargs['ethminer'] = ethminer
                else:
                    kwargs[pass_ethminer] = ethminer

            try:
                f = fn(self, *args, **kwargs)
                if asyncio.iscoroutine(f):
                    await f
            finally:
                if ethminer:
                    ethminer.stop()
                geth.stop()

        return wrapper

    if func is not None:
        return wrap(func)
    else:
        return wrap

def geth_websocket_connect(url, io_loop=None, callback=None, connect_timeout=None,
                           on_message_callback=None, compression_options=None):
    """Helper function for connecting to geth via websockets, which may need the
    origin set should there be no --wsorigin * option set in geth's config"""

    if not isinstance(url, tornado.httpclient.HTTPRequest):
        if url.startswith('wss://'):
            origin = 'https://{}'.format(socket.gethostname())
        else:
            origin = 'http://{}'.format(socket.gethostname())
        url = tornado.httpclient.HTTPRequest(url, headers={'Origin': origin})
    return websocket_connect(url, io_loop=io_loop, callback=callback, connect_timeout=connect_timeout,
                             on_message_callback=on_message_callback, compression_options=compression_options)
