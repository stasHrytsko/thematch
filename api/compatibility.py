import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import random
from datetime import datetime

from flask import Flask, request, jsonify

from utils import get_logger, add_cors, cors_preflight
from services.zodiac import ZodiacService
from services.biorhythm import BiorhythmCalculator
from services.numerology import NumerologyService
from services.descriptions import CompatibilityDescriptions

logger = get_logger(__name__)
app = Flask(__name__)

_zodiac      = ZodiacService()
_biorhythm   = BiorhythmCalculator()
_numerology  = NumerologyService()
_descriptions = CompatibilityDescriptions()


def _validate_date(date_str: str):
    if not date_str or len(date_str.split(".")) != 3:
        raise ValueError("Use DD.MM.YYYY format")
    dt = datetime.strptime(date_str, "%d.%m.%Y")
    if dt > datetime.now():
        raise ValueError("Date cannot be in the future")
    if dt.year < 1900:
        raise ValueError("Date is too far in the past")
    return dt


@app.route("/", methods=["POST", "OPTIONS"])
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
            from database.db import Database
            with Database() as db:
                db.add_check_history(int(user_id), data["date1"], data["date2"], total)
        except Exception as exc:
            logger.warning("Could not save check history: %s", exc)

    return add_cors(jsonify(result), "POST, OPTIONS")
