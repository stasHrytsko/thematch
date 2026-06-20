import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from flask import Flask, request, jsonify

from utils import get_logger, add_cors, cors_preflight
from database.db import Database

logger = get_logger(__name__)
app = Flask(__name__)


@app.route("/", methods=["POST", "OPTIONS"])
@app.route("/api/user", methods=["POST", "OPTIONS"])
def user():
    if request.method == "OPTIONS":
        return cors_preflight("POST, OPTIONS")

    data = request.get_json(silent=True)
    if data is None or "user_id" not in data:
        return add_cors(jsonify({"error": "'user_id' is required"}), "POST, OPTIONS"), 400

    try:
        user_id = int(data["user_id"])
    except (ValueError, TypeError):
        return add_cors(jsonify({"error": "'user_id' must be an integer"}), "POST, OPTIONS"), 400

    username = str(data.get("username", ""))

    try:
        with Database() as db:
            db.create_user(user_id, username)
            row = db.get_user(user_id)

        if row is None:
            return add_cors(jsonify({"error": "Failed to create user"}), "POST, OPTIONS"), 500

        if row.get("birth_date"):
            row["birth_date"] = str(row["birth_date"])

        return add_cors(jsonify(row), "POST, OPTIONS")
    except Exception as exc:
        logger.error("Error in /api/user: %s", exc)
        return add_cors(jsonify({"error": "Database error"}), "POST, OPTIONS"), 500
