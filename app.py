from flask import Flask, request
import os
import hmac
import hashlib
import traceback

app = Flask(__name__)

API_KEY = os.getenv("ASTER_API_KEY")
API_SECRET = os.getenv("ASTER_API_SECRET")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # ✅ 防呆：檢查 API 金鑰是否存在
        if not API_KEY or not API_SECRET:
            print("❌ API 金鑰未設定")
            print("🔍 ASTER_API_KEY =", API_KEY)
            print("🔍 ASTER_API_SECRET =", API_SECRET)
            return {"error": "API key/secret not set"}, 500

        # ✅ 正確解析 JSON
        data = request.get_json(force=True)
        print("📩 JSON 資料：", data)

        # ✅ 取值並處理
        symbol = data.get("symbol", "")
        side = data.get("side", "").upper()
        quantity = float(data.get("quantity", 0))
        strategy = data.get("strategy", "Unknown")

        print(f"📦 下單參數：{side} {symbol} x {quantity} ({strategy})")

        # ✅ 模擬下單邏輯（你可以改成實際 API 呼叫）
        query = f"symbol={symbol}&side={side}&quantity={quantity}"
        signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

        print("✅ 模擬簽名：", signature)
        return {"status": "ok"}, 200

    except Exception as e:
        print("❌ webhook 錯誤：", str(e))
        print("❌ 錯誤追蹤：", traceback.format_exc())
        return {"error": "Invalid JSON or execution error"}, 400
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
