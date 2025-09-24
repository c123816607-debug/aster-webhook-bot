from flask import Flask, request
import time
import requests
import urllib.parse
import json
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

app = Flask(__name__)

USER = "你的 user 地址"
SIGNER = "你的 signer 地址"
PRIVATE_KEY = "你的私鑰"

def sign_payload(payload, ts):
    json_str = json.dumps(payload, sort_keys=True).replace(' ', '').replace('\'','\"')
    encoded = Web3.solidity_keccak(['string', 'address', 'address', 'uint256'], [json_str, USER, SIGNER, ts])
    signable_msg = encode_defunct(hexstr=encoded.hex())
    signed = Account.sign_message(signable_msg, private_key=PRIVATE_KEY)
    return '0x' + signed.signature.hex()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    ts = int(time.time() * 1000)

    payload = {
        "symbol": data["symbol"],
        "side": data["side"],
        "type": data["type"],
        "timeInForce": data.get("timeInForce", "GTC"),
        "quantity": data["quantity"],
        "positionSide": data.get("positionSide", "BOTH"),
        "recvWindow": "50000",
        "timestamp": str(ts),
        "user": USER,
        "signer": SIGNER,
        "nonce": str(ts * 1000)
    }

    payload["signature"] = sign_payload(payload, ts)
    encoded_payload = urllib.parse.urlencode(payload)

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    url = 'https://fapi.asterdex.com/fapi/v3/order'
    response = requests.post(url, data=encoded_payload, headers=headers)
    print("✅ Aster 回應：", response.text)
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)

