# api/feedback.py
# POST /api/feedback — save user feedback to the database.
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import logging
from flask import Flask, request, jsonify, make_response
from database.db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

_MAX_FEEDBACK_LENGTH = 2000


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/", methods=["POST", "OPTIONS"])
@app.route("/api/feedback", methods=["POST", "OPTIONS"])
def feedback():
    if request.method == "OPTIONS":
        return _cors(make_response("", 200))

    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return _cors(jsonify({"error": "'text' field is required"})), 400

    text = data["text"].strip()
    if len(text) < 3:
        return _cors(jsonify({"error": "Feedback is too short (minimum 3 characters)"})), 400
    if len(text) > _MAX_FEEDBACK_LENGTH:
        return _cors(
            jsonify({"error": f"Feedback is too long (maximum {_MAX_FEEDBACK_LENGTH} characters)"})
        ), 400

    user_id = None
    if "user_id" in data:
        try:
            user_id = int(data["user_id"])
        except (ValueError, TypeError):
            pass  # treat invalid user_id as anonymous

    try:
        with Database() as db:
            success = db.save_feedback(user_id, text)
        if success:
            return _cors(jsonify({"status": "ok", "message": "Feedback saved. Thank you!"}))
        return _cors(jsonify({"error": "Failed to save feedback"})), 500
    except Exception as exc:
        logger.error("Error in /api/feedback: %s", exc)
        return _cors(jsonify({"error": "Database error"})), 500
