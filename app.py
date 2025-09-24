from flask import Flask, request, jsonify
import requests, os, logging
from dotenv import load_dotenv
from aster_signer import generate_nonce, prepare_payload, generate_keccak, sign_hash, build_request_body

app = Flask(__name__)
load_dotenv()

ASTER_ORDER_URL = os.getenv("ASTER_ORDER_URL")
ASTER_PRIVATE_KEY = os.getenv("ASTER_PRIVATE_KEY")
USER = os.getenv("USER")
SIGNER = os.getenv("SIGNER")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        biz_params = {
            "symbol": data.get("symbol"),
            "side": data.get("side"),
            "type": data.get("type", "MARKET"),
            "timeInForce": data.get("timeInForce", "GTC"),
            "quantity": data.get("quantity"),
            "price": data.get("price"),
            "positionSide": data.get("positionSide", "BOTH")
        }

        nonce = generate_nonce()
        json_str = prepare_payload(biz_params)
        keccak_hex = generate_keccak(json_str, USER, SIGNER, nonce)
        signature = sign_hash(keccak_hex, ASTER_PRIVATE_KEY)
        final_body = build_request_body(biz_params, USER, SIGNER, nonce, signature)

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(ASTER_ORDER_URL, headers=headers, data=final_body)

        return jsonify({"status": "ok", "response": response.json()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
