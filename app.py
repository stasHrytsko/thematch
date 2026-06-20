"""TheMatch — единое Flask-приложение для деплоя на Vercel.

Vercel деплоит Flask как одну функцию с единым entrypoint (`app`).
Все эндпоинты собраны здесь; статика раздаётся из `public/**` силами Vercel CDN.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random
from datetime import datetime

from flask import Flask, request, jsonify

from utils import get_logger, add_cors, cors_preflight
from services.zodiac import ZodiacService
from services.biorhythm import BiorhythmCalculator
from services.numerology import NumerologyService
from services.descriptions import CompatibilityDescriptions
from database.db import Database

logger = get_logger(__name__)
app = Flask(__name__)

_zodiac       = ZodiacService()
_biorhythm    = BiorhythmCalculator()
_numerology   = NumerologyService()
_descriptions = CompatibilityDescriptions()

_MAX_FEEDBACK_LENGTH = 2000


# ====================================================================== #
# Helpers                                                                  #
# ====================================================================== #

def _validate_date(date_str: str) -> datetime:
    if not date_str or len(date_str.split(".")) != 3:
        raise ValueError("Use DD.MM.YYYY format")
    dt = datetime.strptime(date_str, "%d.%m.%Y")
    if dt > datetime.now():
        raise ValueError("Date cannot be in the future")
    if dt.year < 1900:
        raise ValueError("Date is too far in the past")
    return dt


def _serialise(record: dict) -> dict:
    out = {}
    for key, val in record.items():
        out[key] = val if isinstance(val, (int, float, str, bool, type(None))) else str(val)
    return out


# ====================================================================== #
# POST /api/compatibility — основной расчёт совместимости                  #
# ====================================================================== #

@app.route("/api/compatibility", methods=["POST", "OPTIONS"])
def compatibility():
    if request.method == "OPTIONS":
        return cors_preflight("POST, OPTIONS")

    data = request.get_json(silent=True)
    if data is None:
        return add_cors(jsonify({"error": "Request body must be JSON"}), "POST, OPTIONS"), 400

    if "date1" not in data or "date2" not in data:
        return add_cors(
            jsonify({"error": "Both 'date1' and 'date2' are required"}), "POST, OPTIONS"
        ), 400

    try:
        date1 = _validate_date(data["date1"].strip())
        date2 = _validate_date(data["date2"].strip())
    except ValueError as exc:
        return add_cors(jsonify({"error": str(exc)}), "POST, OPTIONS"), 400

    zodiac_score, zodiac_details = _zodiac.calculate_zodiac_compatibility(date1, date2)
    bio_score,    bio_details    = _biorhythm.calculate_compatibility(date1, date2)
    num_score,    num_details    = _numerology.calculate_compatibility(date1, date2)

    total = round(zodiac_score * 0.35 + bio_score * 0.35 + num_score * 0.30, 1)

    elements_type = _descriptions.get_elements_compatibility_type(
        zodiac_details["element1"], zodiac_details["element2"]
    )

    result = {
        "total": total,
        "total_emoji":  _descriptions.get_emoji(total),
        "total_phrase": _descriptions.get_random_phrase(
            total, _descriptions.GENERAL_COMPATIBILITY_PHRASES
        ),
        "zodiac": {
            "score":       round(zodiac_score, 1),
            "sign1":       zodiac_details["sign1"],
            "sign2":       zodiac_details["sign2"],
            "sign1_name":  _zodiac.get_sign_name(zodiac_details["sign1"]),
            "sign2_name":  _zodiac.get_sign_name(zodiac_details["sign2"]),
            "sign1_description": _descriptions.ZODIAC_DESCRIPTIONS.get(zodiac_details["sign1"], ""),
            "sign2_description": _descriptions.ZODIAC_DESCRIPTIONS.get(zodiac_details["sign2"], ""),
            "element1":       zodiac_details["element1"],
            "element2":       zodiac_details["element2"],
            "element1_emoji": _descriptions.get_element_emoji(zodiac_details["element1"]),
            "element2_emoji": _descriptions.get_element_emoji(zodiac_details["element2"]),
            "signs_score":    round(zodiac_details["signs_compatibility"], 1),
            "elements_score": round(zodiac_details["elements_compatibility"], 1),
            "signs_emoji":    _descriptions.get_emoji(zodiac_details["signs_compatibility"]),
            "elements_emoji": _descriptions.get_emoji(zodiac_details["elements_compatibility"]),
            "signs_phrase":   _descriptions.get_random_phrase(
                zodiac_details["signs_compatibility"],
                _descriptions.ZODIAC_COMPATIBILITY_PHRASES,
            ),
            "elements_phrase": random.choice(
                _descriptions.ELEMENTS_COMPATIBILITY_PHRASES[elements_type]
            ),
        },
        "biorhythm": {
            "score":       round(bio_score, 1),
            "score_emoji": _descriptions.get_emoji(bio_score),
            "total_description": _descriptions.get_biorhythm_description("total", bio_score),
            "rhythms": {
                name: {
                    "score":       round(rhythm["compatibility"], 1),
                    "emoji":       _descriptions.get_emoji(rhythm["compatibility"]),
                    "person1":     round(rhythm["person1"], 1),
                    "person2":     round(rhythm["person2"], 1),
                    "description": _descriptions.get_biorhythm_description(
                        name, rhythm["compatibility"]
                    ),
                }
                for name, rhythm in bio_details["rhythms"].items()
            },
        },
        "numerology": {
            "score":       round(num_score, 1),
            "score_emoji": _descriptions.get_emoji(num_score),
            "number1":     num_details["number1"],
            "number2":     num_details["number2"],
            "number1_description": _descriptions.NUMEROLOGY_DESCRIPTIONS.get(
                num_details["number1"], ""
            ),
            "number2_description": _descriptions.NUMEROLOGY_DESCRIPTIONS.get(
                num_details["number2"], ""
            ),
            "partnership_number":      num_details["partnership_number"],
            "partnership_description": num_details["partnership_description"],
            "phrase": _descriptions.get_random_phrase(
                num_score, _descriptions.NUMEROLOGY_COMPATIBILITY_PHRASES
            ),
        },
    }

    user_id = data.get("user_id")
    if user_id is not None:
        try:
            with Database() as db:
                db.add_check_history(int(user_id), data["date1"], data["date2"], total)
        except Exception as exc:
            logger.warning("Could not save check history: %s", exc)

    return add_cors(jsonify(result), "POST, OPTIONS")


# ====================================================================== #
# POST /api/user — создать/получить пользователя                           #
# ====================================================================== #

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


# ====================================================================== #
# POST /api/feedback — сохранить отзыв                                     #
# ====================================================================== #

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


# ====================================================================== #
# GET /api/history?user_id=&limit= — история проверок                      #
# ====================================================================== #

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
