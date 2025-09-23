from flask import Flask, request
import requests, time, hmac, hashlib
import os

app = Flask(__name__)

API_KEY = os.getenv("ASTER_API_KEY")
API_SECRET = os.getenv("ASTER_API_SECRET")
BASE_URL = "https://fapi.asterdex.com"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    symbol = data['symbol']
    side = data['side']
    quantity = data['quantity']
    strategy = data.get('strategy', 'default')
    position_size = data.get('position_size', 0)

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
    headers = {"X-API-KEY": API_KEY}
    requests.post(f"{BASE_URL}/fapi/v3/leverage", params=payload, headers=headers)

def place_order(symbol, side, quantity):
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
    headers = {"X-API-KEY": API_KEY}
    response = requests.post(f"{BASE_URL}/fapi/v3/order", params=payload, headers=headers)
    return response.text, response.status_code
  
