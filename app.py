from flask import Flask, request
import time, requests, urllib.parse, json, os
from dotenv import load_dotenv
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

# 🚀 啟動 Flask
app = Flask(__name__)
load_dotenv()

# 📦 載入環境變數
USER = os.getenv("USER")
SIGNER = os.getenv("SIGNER")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
if PRIVATE_KEY and PRIVATE_KEY.startswith("0x"):
    PRIVATE_KEY = PRIVATE_KEY[2:]

# 🔐 簽名函式
def sign_payload(payload, ts):
    json_str = json.dumps(payload, sort_keys=True).replace(' ', '').replace('\'','\"')
    encoded = Web3.solidity_keccak(['string', 'address', 'address', 'uint256'], [json_str, USER, SIGNER, ts])
    signable_msg = encode_defunct(hexstr=encoded.hex())
    signed = Account.sign_message(signable_msg, private_key=PRIVATE_KEY)
    return '0x' + signed.signature.hex()

# 📩 webhook 路由
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        if not USER or not SIGNER or not PRIVATE_KEY:
            raise ValueError("❌ USER / SIGNER / PRIVATE_KEY 未設定")

        print("📩 收到 webhook")
        data = request.get_json(force=True)
        print("📦 webhook 內容：", data)

        symbol = data.get("symbol")
        side = data.get("side")
        type_ = data.get("type")
        quantity = data.get("quantity")

        if not symbol or not side or not type_ or not quantity:
            raise ValueError("❌ webhook JSON 缺少必要欄位")

        ts = int(time.time() * 1000)
        print("🕒 timestamp：", ts)

        payload = {
            "symbol": symbol,
            "side": side,
            "type": type_,
            "timeInForce": data.get("timeInForce", "GTC"),
            "quantity": quantity,
            "positionSide": data.get("positionSide", "BOTH"),
            "recvWindow": "50000",
            "timestamp": str(ts),
            "user": USER,
            "signer": SIGNER,
            "nonce": str(ts * 1000)
        }

        print("🔐 正在簽名")
        payload["signature"] = sign_payload(payload, ts)

        encoded_payload = urllib.parse.urlencode(payload)
        print("📦 encoded payload：", encoded_payload)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        url = 'https://fapi.asterdex.com/fapi/v3/order'
        print("🚀 發送到 Aster：", url)
        response = requests.post(url, data=encoded_payload, headers=headers, timeout=5)

        print("✅ Aster 回應：", response.text)
        return {'status': 'ok'}
    except Exception as e:
        print("❌ webhook 錯誤：", str(e))
        return {'error': str(e)}, 500

# 🟢 啟動 Flask 伺服器
if __name__ == '__main__':
    print("🚀 webhook bot 啟動成功，等待 TradingView 訊號…")
    app.run(host='0.0.0.0', port=8000)
