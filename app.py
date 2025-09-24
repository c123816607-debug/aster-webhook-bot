#!/usr/bin/env python3
print("🟢 app.py 開始執行")

import os
import time
import hmac
import hashlib
import logging
import urllib.parse
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# 啟用 dotenv（本地開發用）
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Flask
app = Flask(__name__)

# 環境變數（在 Railway 或 GitHub Secrets 設定）
ASTER_API_KEY = os.getenv("ASTER_API_KEY")       # 必填：Aster 提供的 API Key
ASTER_SECRET_KEY = os.getenv("ASTER_SECRET_KEY") # 必填：Aster 提供的 Secret Key
ASTER_ORDER_URL = os.getenv("ASTER_ORDER_URL", "https://fapi.asterdex.com/fapi/v3/order")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() in ("1","true","yes")
RECV_WINDOW = os.getenv("RECV_WINDOW", "50000")

# 可選（以前 code 有的欄位）
USER = os.getenv("USER")     # optional, 若 API 不需要可不設
SIGNER = os.getenv("SIGNER") # optional

def sign_query_string(query_string: str, secret: str) -> str:
    """
    用 HMAC-SHA256簽名 query_string，回傳 hex string
    """
    if isinstance(secret, str):
        secret = secret.encode('utf-8')
    if isinstance(query_string, str):
        query_string = query_string.encode('utf-8')
    signature = hmac.new(secret, query_string, hashlib.sha256).hexdigest()
    return signature

def build_signed_payload(params: dict) -> dict:
    """
    將 params 轉成 query string（不含 signature），產生 signature 並回傳包含 signature 的 dict
    - 參數排序採 urllib.parse.urlencode（字典 iteration 的預設順序），
      若需要「字典序排序」，請改用 sorted(params.items())。
    """
    # Add timestamp and recvWindow
    params["timestamp"] = str(int(time.time() * 1000))
    params["recvWindow"] = params.get("recvWindow", RECV_WINDOW)

    # 注意：Aster/類Binance 的簽名通常是 key=val&key2=val2（URL encoding）
    # 若你們官方文件要求按字典排序，請用 sorted(params.items())。
    # 這裡採穩健做法：按字典序排序，避免順序問題。
    items = sorted([(k, str(v)) for k, v in params.items()])
    qs = urllib.parse.urlencode(items)

    signature = sign_query_string(qs, ASTER_SECRET_KEY)
    params["signature"] = signature
    return params, qs

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        logging.info("🔔 收到 webhook 請求")

        if not ASTER_API_KEY or not ASTER_SECRET_KEY:
            logging.error("❌ 未設定 ASTER_API_KEY 或 ASTER_SECRET_KEY")
            return jsonify({"error": "Server misconfiguration: missing API keys"}), 500

        try:
            data = request.get_json(force=True)
        except Exception as e:
            logging.error("❌ JSON 解析失敗: %s", e)
            return jsonify({"error": "Invalid JSON"}), 400

        logging.info("📦 webhook JSON: %s", data)

        symbol = data.get("symbol")
        side = data.get("side")
        type_ = data.get("type") or data.get("orderType")
        quantity = data.get("quantity")
        time_in_force = data.get("timeInForce", "GTC")
        position_side = data.get("positionSide", "BOTH")
        user = data.get("user") or USER
        signer = data.get("signer") or SIGNER

        if not all([symbol, side, type_, quantity]):
            logging.error("❌ 缺少必要欄位")
            return jsonify({"error": "Missing required fields"}), 400

        # 建立 payload
        payload = {
            "symbol": symbol,
            "side": side.upper(),
            "type": type_.upper(),
            "quantity": str(quantity),
            "timeInForce": time_in_force,
            "positionSide": position_side,
            "nonce": str(int(time.time() * 1000)),
            "timestamp": str(int(time.time() * 1000)),
            "recvWindow": RECV_WINDOW
        }

        if user:
            payload["user"] = user
        if signer:
            payload["signer"] = signer

        logging.info(f"🔑 USER={user}, SIGNER={signer}")
        logging.info("📤 最終 payload: %s", payload)

        if payload["type"] == "LIMIT":
            price = data.get("price")
            if not price:
                return jsonify({"error": "LIMIT order requires price"}), 400
            payload["price"] = str(price)

        signed_params, _ = build_signed_payload(payload.copy())
        final_qs = urllib.parse.urlencode(sorted(signed_params.items()))

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-MBX-APIKEY": ASTER_API_KEY
        }

        logging.info("🔐 已建立簽名，TEST_MODE=%s", TEST_MODE)

        if TEST_MODE:
            logging.info("🧪 TEST MODE: 不會發送真實請求。Final QS: %s", final_qs)
            return jsonify({
                "status": "test",
                "final_qs": final_qs,
                "endpoint": ASTER_ORDER_URL,
                "headers": {"X-MBX-APIKEY": "REDACTED"},
            }), 200

        resp = requests.post(ASTER_ORDER_URL, data=final_qs, headers=headers, timeout=10)
        logging.info("📨 發送到 %s，HTTP %s", ASTER_ORDER_URL, resp.status_code)

        try:
            resp_json = resp.json()
        except ValueError:
            resp_text = resp.text
            logging.error("❌ 非 JSON 回應: %s", resp_text)
            return jsonify({"error": "Non-JSON response", "text": resp_text}), resp.status_code

        if resp.status_code not in (200, 201):
            logging.error("❌ 下單失敗 HTTP %s: %s", resp.status_code, resp_json)
            return jsonify({"error": "order failed", "detail": resp_json}), resp.status_code

        logging.info("✅ 下單成功: %s", resp_json)
        return jsonify({"status": "ok", "result": resp_json}), 200

    except Exception as e:
        logging.exception("❌ webhook 處理例外")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logging.info("🚀 webhook bot 啟動，PORT=%s, TEST_MODE=%s", port, TEST_MODE)
    app.run(host="0.0.0.0", port=port)
