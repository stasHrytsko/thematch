import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from flask import Flask, request, jsonify

from utils import get_logger, add_cors, cors_preflight
from database.db import Database

logger = get_logger(__name__)
app = Flask(__name__)

_MAX_FEEDBACK_LENGTH = 2000


@app.route("/", methods=["POST", "OPTIONS"])
@app.route("/api/feedback", methods=["POST", "OPTIONS"])
def feedback():
    if request.method == "OPTIONS":
        return cors_preflight("POST, OPTIONS")

    data = request.get_json(silent=True)
    if data is None or "text" not in data:
        return add_cors(jsonify({"error": "'text' field is required"}), "POST, OPTIONS"), 400

    text = data["text"].strip()
    if len(text) < 3:
        return add_cors(
            jsonify({"error": "Feedback is too short (minimum 3 characters)"}), "POST, OPTIONS"
        ), 400
    if len(text) > _MAX_FEEDBACK_LENGTH:
        return add_cors(
            jsonify({"error": f"Feedback is too long (maximum {_MAX_FEEDBACK_LENGTH} characters)"}),
            "POST, OPTIONS",
        ), 400

    user_id = None
    if "user_id" in data:
        try:
            user_id = int(data["user_id"])
        except (ValueError, TypeError):
            pass

    try:
        with Database() as db:
            success = db.save_feedback(user_id, text)
        if success:
            return add_cors(
                jsonify({"status": "ok", "message": "Feedback saved. Thank you!"}), "POST, OPTIONS"
            )
        return add_cors(jsonify({"error": "Failed to save feedback"}), "POST, OPTIONS"), 500
    except Exception as exc:
        logger.error("Error in /api/feedback: %s", exc)
        return add_cors(jsonify({"error": "Database error"}), "POST, OPTIONS"), 500
