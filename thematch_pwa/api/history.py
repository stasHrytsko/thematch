import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from flask import Flask, request, jsonify

from utils import get_logger, add_cors, cors_preflight
from database.db import Database

logger = get_logger(__name__)
app = Flask(__name__)


def _serialise(record: dict) -> dict:
    out = {}
    for key, val in record.items():
        out[key] = str(val) if not isinstance(val, (int, float, str, bool, type(None))) else val
    return out


@app.route("/", methods=["GET", "OPTIONS"])
@app.route("/api/history", methods=["GET", "OPTIONS"])
def history():
    if request.method == "OPTIONS":
        return cors_preflight("GET, OPTIONS")

    user_id_raw = request.args.get("user_id")
    if not user_id_raw:
        return add_cors(
            jsonify({"error": "'user_id' query parameter is required"}), "GET, OPTIONS"
        ), 400

    try:
        user_id = int(user_id_raw)
    except ValueError:
        return add_cors(jsonify({"error": "'user_id' must be an integer"}), "GET, OPTIONS"), 400

    limit_raw = request.args.get("limit", "10")
    try:
        limit = max(1, min(int(limit_raw), 50))
    except ValueError:
        limit = 10

    try:
        with Database() as db:
            records = db.get_history(user_id, limit)
        return add_cors(jsonify({"history": [_serialise(r) for r in records]}), "GET, OPTIONS")
    except Exception as exc:
        logger.error("Error in /api/history: %s", exc)
        return add_cors(jsonify({"error": "Database error"}), "GET, OPTIONS"), 500
