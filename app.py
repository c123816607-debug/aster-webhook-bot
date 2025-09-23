from flask import Flask, request
import requests, time, hmac, hashlib, traceback
import os

app = Flask(__name__)

API_KEY = os.getenv("ASTER_API_KEY")
API_SECRET = os.getenv("ASTER_API_SECRET")
BASE_URL = "https://fapi.asterdex.com"

def clean_symbol(symbol):
    return symbol.replace(".P", "") if symbol else ""

@app.route('/webhook', methods=['POST'])
def webhook():
    print("📩 Webhook 被觸發")
    print("📩 原始資料：", request.data)

    try:
        data = request.get_json(force=True)
        print("📩 JSON 資料：", data)

        if not data:
            print("❌ 沒有收到 JSON")
            return {"error": "Missing JSON"}, 400

        symbol = clean_symbol(data.get('symbol'))
        side = data.get('side')
        quantity = data.get('quantity')
        strategy = data.get('strategy', 'default')
        position_size = data.get('position_size', 0)

        # 防錯：檢查必要欄位
        if not symbol or not side or quantity is None:
            print("❌ 缺少必要欄位")
            return {"error": "Missing symbol/side/quantity"}, 400

        # 防錯：檢查 API 金鑰
        if not API_KEY or not API_SECRET:
            print("❌ API 金鑰未設定")
            return {"error": "API key/secret not set"}, 500

        # 防錯：檢查 quantity 格式
        try:
            quantity = float(quantity)
        except (TypeError, ValueError):
            print("❌ quantity 格式錯誤")
            return {"error": "Invalid quantity format"}, 400

        print(f"📦 下單參數：symbol={symbol}, side={side}, quantity={quantity}")

        set_leverage(symbol, 20)
        result, status = place_order(symbol, side, quantity)

        return {
            "status": "success" if status == 200 else "error",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "response": result
        }, status

    except Exception as e:
        print("❌ webhook 錯誤：", str(e))
        print("❌ 錯誤追蹤：", traceback.format_exc())
        return {"error": str(e)}, 500

def set_leverage(symbol, leverage):
    timestamp = int(time.time() * 1000)
    query = f"symbol={symbol}&leverage={leverage}&timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    payload = {
        "symbol": symbol,
        "leverage": leverage,
        "timestamp": timestamp,
        "signature": signature
    }
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(f"{BASE_URL}/fapi/v3/leverage", json=payload, headers=headers)
    print("⚙️ 設定槓桿回應：", response.text)

def place_order(symbol, side, quantity):
    try:
        timestamp = int(time.time() * 1000)
        query = f"symbol={symbol}&side={side}&type=MARKET&quantity={quantity}&recvWindow=5000&timestamp={timestamp}"
        signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

        payload = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
            "recvWindow": 5000,
            "timestamp": timestamp,
            "signature": signature
        }

        headers = {
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json"
        }

        print("📤 下單 Payload：", payload)

        response = requests.post(f"{BASE_URL}/fapi/v3/order", json=payload, headers=headers)

        print("✅ API 回應：", response.text)
        print("🔁 回應狀態碼：", response.status_code)

        return response.text, response.status_code

    except Exception as e:
        print("❌ 下單錯誤：", str(e))
        print("❌ 錯誤追蹤：", traceback.format_exc())
        return str(e), 500
