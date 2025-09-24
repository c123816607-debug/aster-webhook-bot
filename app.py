print("🟢 app.py 開始執行")

from flask import Flask, request
import time, math, json, requests, os
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_abi import encode
from web3 import Web3

app = Flask(__name__)
load_dotenv()

USER = os.getenv("USER")
SIGNER = os.getenv("SIGNER")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# ✅ Aster 要求完整 hex 格式 → 不要去掉 0x
if not PRIVATE_KEY.startswith("0x"):
    PRIVATE_KEY = "0x" + PRIVATE_KEY

def _trim_dict(d):
    for key in d:
        value = d[key]
        if isinstance(value, list):
            new_value = []
            for item in value:
                new_value.append(json.dumps(_trim_dict(item)) if isinstance(item, dict) else str(item))
            d[key] = json.dumps(new_value)
        elif isinstance(value, dict):
            d[key] = json.dumps(_trim_dict(value))
        else:
            d[key] = str(value)
    return d

def sign_payload(payload, nonce):
    _trim_dict(payload)
    json_str = json.dumps(payload, sort_keys=True).replace(' ', '').replace('\'','\"')
    print("🔐 json_str:", json_str)

    encoded = encode(['string', 'address', 'address', 'uint256'], [json_str, USER, SIGNER, nonce])
    keccak_hex = Web3.keccak(encoded).hex()
    print("🔐 keccak:", keccak_hex)

    signable_msg = encode_defunct(hexstr=keccak_hex)
    signed = Account.sign_message(signable_msg, private_key=PRIVATE_KEY)
    return '0x' + signed.signature.hex()

@app.route('/ping')
def ping():
    return "pong"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("🟢 webhook 進入")
        data = request.get_json(force=True)
        print("📦 webhook 內容：", data)

        ts = int(time.time() * 1000)
        nonce = math.trunc(time.time() * 1_000_000)

        payload = {
            "symbol": str(data.get("symbol")),
            "side": str(data.get("side")),
            "type": str(data.get("type")),
            "quantity": str(data.get("quantity")),
            "price": str(data.get("price")),
            "timeInForce": str(data.get("timeInForce", "GTC")),
            "positionSide": str(data.get("positionSide", "BOTH")),
            "recvWindow": "50000",
            "timestamp": str(ts)
        }

        signature = sign_payload(payload, nonce)

        payload["nonce"] = str(nonce)
        payload["user"] = USER
        payload["signer"] = SIGNER
        payload["signature"] = signature

        url = 'https://fapi.asterdex.com/fapi/v3/order'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'PythonApp/1.0'
        }

        print("🚀 發送到 Aster：", url)
        print("📦 payload：", payload)

        try:
            res = requests.post(url, data=payload, headers=headers, timeout=5)
            print("✅ Aster 回應：", res.text)
            return {'status': 'ok', 'response': res.text}
        except Exception as e:
            print("❌ POST 失敗：", str(e))
            return {'error': 'Aster unreachable'}, 502

    except Exception as e:
        print("❌ webhook 錯誤：", str(e))
        return {'error': str(e)}, 500

if __name__ == '__main__':
    print("🚀 webhook bot 啟動成功，等待 TradingView 訊號…")
    app.run(host='0.0.0.0', port=8000)
