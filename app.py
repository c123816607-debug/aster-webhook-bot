from flask import Flask, request
import os, time, json, traceback, requests
from eth_account import Account
from eth_abi import encode
from web3 import Web3
from eth_account.messages import encode_defunct

app = Flask(__name__)

# ✅ 環境變數讀取
USER = os.getenv("ASTER_USER")
SIGNER = os.getenv("ASTER_SIGNER")
PRIVATE_KEY = os.getenv("ASTER_PK")

print("🔍 USER:", USER)
print("🔍 SIGNER:", SIGNER)
print("🔍 PRIVATE_KEY:", PRIVATE_KEY)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # ✅ 解析 TradingView 傳入 JSON
        data = request.get_json(force=True)
        print("📩 JSON 資料：", data)

        # ✅ Step 1：清洗參數
        data = {k: v for k, v in data.items() if v is not None}
        data['recvWindow'] = 50000
        data['timestamp'] = int(time.time() * 1000)

        # ✅ 強制將 side 轉成大寫
        if 'side' in data:
            data['side'] = data['side'].upper()

        # ✅ 清洗 dict：將 list、dict 轉成 JSON 字串
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

        _trim_dict(data)

        # ✅ 排序後轉成 JSON 字串（準備簽名）
        json_str = json.dumps(data, sort_keys=True).replace(' ', '').replace('\'','\"')
        print("📦 排序後參數：", json_str)

        # ✅ Step 2：生成 nonce + ABI 編碼 + keccak hash
        nonce = int(time.time() * 1_000_000)
        encoded = encode(['string', 'address', 'address', 'uint256'], [json_str, USER, SIGNER, nonce])
        keccak_hex = Web3.keccak(encoded).hex()
        print("🔐 keccak hash：", keccak_hex)

        # ✅ Step 3：用 signer 私鑰簽名
        signable_msg = encode_defunct(hexstr=keccak_hex)
        signed = Account.sign_message(signable_msg, private_key=PRIVATE_KEY)
        signature = '0x' + signed.signature.hex()
        print("🖋️ 簽名結果：", signature)

        # ✅ Step 4：組裝請求
        data.update({
            'nonce': nonce,
            'user': USER,
            'signer': SIGNER,
            'signature': signature
        })

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'PythonApp/1.0'
        }

        url = 'https://fapi.asterdex.com/fapi/v3/order'
        response = requests.post(url, data=data, headers=headers)

        # ✅ Step 5：錯誤防呆（避免 .json() 炸掉）
        try:
            result = response.json()
        except Exception:
            print("❌ 無法解析 JSON，回傳內容：", response.text)
            result = {"raw": response.text}

        print("✅ Aster 回應：", response.status_code, result)
        return {"status": "ok", "response": result}, response.status_code

    except Exception as e:
        print("❌ webhook 錯誤：", str(e))
        print("❌ 錯誤追蹤：", traceback.format_exc())
        return {"error": "execution error"}, 400
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

