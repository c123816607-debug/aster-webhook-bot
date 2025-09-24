import time, math, json
from eth_abi import encode
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

def generate_nonce():
    return math.trunc(time.time() * 1_000_000)

def _trim_dict(my_dict):
    for key in my_dict:
        value = my_dict[key]
        if isinstance(value, list):
            new_value = []
            for item in value:
                new_value.append(json.dumps(_trim_dict(item)) if isinstance(item, dict) else str(item))
            my_dict[key] = json.dumps(new_value)
        elif isinstance(value, dict):
            my_dict[key] = json.dumps(_trim_dict(value))
        else:
            my_dict[key] = str(value)
    return my_dict

def prepare_payload(biz_params):
    biz_params = {k: v for k, v in biz_params.items() if v is not None}
    biz_params["recvWindow"] = 50000
    biz_params["timestamp"] = int(time.time() * 1000)
    _trim_dict(biz_params)
    json_str = json.dumps(biz_params, sort_keys=True).replace(" ", "").replace("'", '"')
    return json_str

def generate_keccak(json_str, user, signer, nonce):
    encoded = encode(['string', 'address', 'address', 'uint256'], [json_str, user, signer, nonce])
    return Web3.keccak(encoded).hex()

def sign_hash(keccak_hex, private_key):
    signable_msg = encode_defunct(hexstr=keccak_hex)
    signed = Account.sign_message(signable_msg, private_key=private_key)
    return '0x' + signed.signature.hex()

def build_request_body(biz_params, user, signer, nonce, signature):
    biz_params["nonce"] = nonce
    biz_params["user"] = user
    biz_params["signer"] = signer
    biz_params["signature"] = signature
    return biz_params
