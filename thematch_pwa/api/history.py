# api/history.py
# GET /api/history?user_id=X — return a user's recent compatibility checks.
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
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _serialise(record: dict) -> dict:
    """Convert non-JSON-serialisable values (datetime, date) to strings."""
    out = {}
    for key, val in record.items():
        out[key] = str(val) if not isinstance(val, (int, float, str, bool, type(None))) else val
    return out


@app.route("/", methods=["GET", "OPTIONS"])
@app.route("/api/history", methods=["GET", "OPTIONS"])
def history():
    if request.method == "OPTIONS":
        return _cors(make_response("", 200))

    user_id_raw = request.args.get("user_id")
    if not user_id_raw:
        return _cors(jsonify({"error": "'user_id' query parameter is required"})), 400

    try:
        user_id = int(user_id_raw)
    except ValueError:
        return _cors(jsonify({"error": "'user_id' must be an integer"})), 400

    limit_raw = request.args.get("limit", "10")
    try:
        limit = max(1, min(int(limit_raw), 50))  # cap between 1 and 50
    except ValueError:
        limit = 10

    try:
        with Database() as db:
            records = db.get_history(user_id, limit)
        return _cors(jsonify({"history": [_serialise(r) for r in records]}))
    except Exception as exc:
        logger.error("Error in /api/history: %s", exc)
        return _cors(jsonify({"error": "Database error"})), 500
