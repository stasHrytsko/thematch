# api/user.py
# POST /api/user — create or retrieve a user record.
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import logging
from flask import Flask, request, jsonify, make_response
from database.db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/", methods=["POST", "OPTIONS"])
@app.route("/api/user", methods=["POST", "OPTIONS"])
def user():
    if request.method == "OPTIONS":
        return _cors(make_response("", 200))

    data = request.get_json(silent=True)
    if not data or "user_id" not in data:
        return _cors(jsonify({"error": "'user_id' is required"})), 400

    try:
        user_id = int(data["user_id"])
    except (ValueError, TypeError):
        return _cors(jsonify({"error": "'user_id' must be an integer"})), 400

    username = str(data.get("username", ""))

    try:
        with Database() as db:
            db.create_user(user_id, username)
            row = db.get_user(user_id)

        if row is None:
            return _cors(jsonify({"error": "Failed to create user"})), 500

        # Convert date objects to ISO strings for JSON serialisation
        if row.get("birth_date"):
            row["birth_date"] = str(row["birth_date"])

        return _cors(jsonify(row))
    except Exception as exc:
        logger.error("Error in /api/user: %s", exc)
        return _cors(jsonify({"error": "Database error"})), 500
