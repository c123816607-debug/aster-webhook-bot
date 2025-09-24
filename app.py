import os, time, json, hmac, hashlib, logging
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# 初始化 Flask
app = Flask(__name__)
load_dotenv()

# 設定 log
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 環境變數
ASTER_ORDER_URL = os.getenv("ASTER_ORDER_URL", "https://fapi.asterdex.com/fapi/v3/order")
ASTER_API_KEY = os.getenv("ASTER_API_KEY")
ASTER_API_SECRET = os.getenv("ASTER_API_SECRET")
USER = os.getenv("USER")
SIGNER = os.getenv("SIGNER")

# ===== 簽名函式 =====
def build_signed_payload(params: dict) -> str:
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        ASTER_API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return query_string + "&signature=" + signature

# ===== webhook 路由 =====
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

        # 準備參數
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "timeInForce": time_in_force,
            "quantity": quantity,
            "timestamp": int(time.time() * 1000),
            "user": USER,
            "signer": SIGNER,
        }

        # debug log
        logger.info(f"🔑 USER={USER}, SIGNER={SIGNER}")
        logger.info(f"📦 下單參數: {params}")

        final_qs = build_signed_payload(params)

        headers = {"X-MBX-APIKEY": ASTER_API_KEY}
        response = requests.post(ASTER_ORDER_URL, headers=headers, data=final_qs)

        logger.info(f"🛠 發送到: {ASTER_ORDER_URL}")
        logger.info(f"📤 發送內容: {final_qs}")
        logger.info(f"📥 回應: {response.text}")

        return jsonify({"status": "ok", "response": response.json()})

    except Exception as e:
        logger.error(f"❌ webhook 錯誤: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 啟動 Flask
if __name__ == "__main__":
    logger.info("🚀 Webhook bot 啟動成功，等待 TradingView 訊號...")
    app.run(host="0.0.0.0", port=8000)
