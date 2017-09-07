"""Token Request helpers"""

from ethereum.utils import sha3
import base64
import json

from .ethereum.utils import sign_payload
from .utils import str_types, parse_int

TOKEN_SIGNATURE_DATA_STRING = "{VERB}\n{PATH}\n{TIMESTAMP}\n{HASH}"

def generate_request_signature_data_string(method, path, timestamp, data):

    if isinstance(data, str_types):
        data = data.encode('utf-8')
    elif isinstance(data, dict):
        data = json.dumps(data).encode('utf-8')

    if data is not None and data != b"":
        datahash = base64.b64encode(sha3(data)).decode('utf-8')
    else:
        datahash = ""

    # make sure the timestamp is an integer
    timestamp = parse_int(timestamp)

    method = method.upper()

    return TOKEN_SIGNATURE_DATA_STRING.format(VERB=method, PATH=path, TIMESTAMP=timestamp, HASH=datahash).encode('utf-8')

def sign_request(private_key, method, path, timestamp, data):

    data_string = generate_request_signature_data_string(method, path, timestamp, data)

    return sign_payload(private_key, data_string)
