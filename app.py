from flask import Flask, request
import requests, time, hmac, hashlib
import os

app = Flask(__name__)

API_KEY = os.getenv("ASTER_API_KEY")
API_SECRET = os.getenv("ASTER_API_SECRET")
BASE_URL = "https://fapi.asterdex.com"

def clean_symbol(symbol):
    return symbol.replace(".P", "")

@app.route('/webhook', methods=['POST'])
def webhook():
    print("📩 Webhook 被觸發")
    print("📩 原始資料：", request.data)

    data = request.get_json()
    print("📩 JSON 資料：", data)

    if not data:
        return "❌ 沒有收到 JSON", 400

    symbol = clean_symbol(data.get('symbol'))
    side = data.get('side')
    quantity = data.get('quantity')
    strategy = data.get('strategy', 'default')
    position_size = data.get('position_size', 0)

    print("📦 下單參數：", symbol, side, quantity)

    set_leverage(symbol, 20)
    return place_order(symbol, side, quantity)

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
        query = f"symbol={symbol}&side={side}&type=MARKET&quantity={quantity}&timestamp={timestamp}"
        signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

        payload = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
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
        return str(e), 500
