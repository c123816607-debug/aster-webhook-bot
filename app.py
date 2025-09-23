from flask import Flask, request
import time, hmac, hashlib, requests
from eth_account import Account
from web3 import Web3

app = Flask(__name__)

USER = os.getenv("ASTER_USER")         # 主帳戶地址
SIGNER = os.getenv("ASTER_SIGNER")     # API 錢包地址
PRIVATE_KEY = os.getenv("ASTER_PK")    # signer 的私鑰

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        symbol = data.get("symbol", "")
        side = data.get("side", "").upper()
        quantity = str(data.get("quantity", ""))
        strategy = data.get("strategy", "FundingArb")

        nonce = str(int(time.time() * 1_000_000))  # 微秒
        timestamp = str(int(time.time() * 1000))   # 毫秒

        # 所有參數轉成字串並排序
        params = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "strategy": strategy,
            "user": USER,
            "signer": SIGNER,
            "nonce": nonce
        }
        sorted_items = sorted(params.items())
        encoded = Web3.solidityKeccak(
            ['string'] * len(sorted_items),
            [str(v) for k, v in sorted_items]
        )

        # 用 signer 私鑰簽名
        acct = Account.from_key(PRIVATE_KEY)
        signature = acct.signHash(encoded).signature.hex()

        # 發送請求
        payload = {
            **params,
            "signature": signature,
            "timestamp": timestamp,
            "recvWindow": "5000"
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        response = requests.post("https://fapi.asterdex.com/fapi/v3/order", data=payload, headers=headers)
        print("✅ API 回應：", response.status_code, response.text)
        return {"status": "ok", "response": response.json()}, 200

    except Exception as e:
        print("❌ webhook 錯誤：", str(e))
        return {"error": "execution error"}, 400
