import os, time, hmac, hashlib, logging
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ASTER_ORDER_URL = os.getenv("ASTER_ORDER_URL", "https://fapi.asterdex.com/fapi/v3/order")
ASTER_API_KEY = os.getenv("ASTER_API_KEY")
ASTER_API_SECRET = os.getenv("ASTER_API_SECRET")
USER = os.getenv("USER")
SIGNER = os.getenv("SIGNER")

def build_signature(params: dict) -> str:
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return hmac.new(
        ASTER_API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        logger.info(f"🔔 收到 webhook 請求: {data}")

        symbol = data.get("symbol")
        side = data.get("side")
        order_type = data.get("type", "MARKET")
        time_in_force = data.get("timeInForce", "GTC")
        quantity = data.get("quantity")

        if not symbol or not side or not quantity:
            return jsonify({"error": "缺少必要參數"}), 400

        # 組裝參數
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "timeInForce": time_in_force,
            "quantity": quantity,
            "timestamp": int(time.time() * 1000),
            "nonce": int(time.time() * 1_000_000),
            "user": USER,
            "signer": SIGNER,
        }

        # 全部轉成字串
        params = {k: str(v) for k, v in params.items()}

        # 加入簽名
        signature = build_signature(params)
        params["signature"] = signature

        logger.info(f"📦 下單參數: {params}")
        logger.info(f"🛠 發送到: {ASTER_ORDER_URL}")

        headers = {
            "X-MBX-APIKEY": ASTER_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # 用 params 傳送（不是 data）
        response = requests.post(ASTER_ORDER_URL, headers=headers, date=params)
        logger.info(f"📥 回應: {response.text}")

        try:
            return jsonify({"status": "ok", "response": response.json()})
        except ValueError:
            return jsonify({"status": "ok", "raw": response.text})

    except Exception as e:
        logger.error(f"❌ webhook 錯誤: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("🚀 Webhook bot 啟動成功，等待 TradingView 訊號...")
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
