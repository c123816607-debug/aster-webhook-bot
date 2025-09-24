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

def build_signed_payload(params: dict) -> str:
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        ASTER_API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return query_string + "&signature=" + signature

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
        user = data.get("user") or USER
        signer = data.get("signer") or SIGNER

        if not symbol or not side or not quantity:
            return jsonify({"error": "缺少必要參數"}), 400

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "timeInForce": time_in_force,
            "quantity": quantity,
            "timestamp": int(time.time() * 1000),
            "recvWindow": "50000",
            "nonce": str(int(time.time() * 1000)),
            "user": user,
            "signer": signer,
        }

        logger.info(f"🔑 USER={user}, SIGNER={signer}")
        logger.info(f"📦 下單參數: {params}")

        final_qs = build_signed_payload(params)
        headers = {"X-MBX-APIKEY": ASTER_API_KEY}
        response = requests.post(ASTER_ORDER_URL, headers=headers, data=final_qs)

        logger.info(f"🛠 發送到: {ASTER_ORDER_URL}")
        logger.info(f"📤 發送內容: {final_qs}")
        logger.info(f"📥 回應: {response.text}")

        try:
            return jsonify({"status": "ok", "response": response.json()})
        except Exception:
            return jsonify({"status": "error", "raw": response.text}), response.status_code

    except Exception as e:
        logger.error(f"❌ webhook 錯誤: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "alive"}), 200

if __name__ == "__main__":
    logger.info("🚀 Webhook bot 啟動成功，等待 TradingView 訊號...")
    app.run(host="0.0.0.0", port=8000)
