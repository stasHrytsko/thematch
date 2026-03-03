# api/webhook.py
# POST /api/webhook — Telegram webhook endpoint.
# Receives updates from Telegram and processes them via the bot library,
# allowing the bot to run as a serverless function alongside the PWA.
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import json
import logging
from flask import Flask, request, jsonify, make_response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")


def _cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def _get_bot():
    """Lazily import and configure the bot. Returns None if token is missing."""
    if not BOT_TOKEN:
        return None
    try:
        import telebot
        from database.db import Database
        from services.zodiac import ZodiacService
        from services.biorhythm import BiorhythmCalculator
        from services.numerology import NumerologyService
        from services.descriptions import CompatibilityDescriptions
        from handlers.start import register_start_handlers
        from handlers.compatibility import register_compatibility_handlers
        from handlers.feedback import register_feedback_handlers

        bot = telebot.TeleBot(BOT_TOKEN)
        db = Database()
        register_start_handlers(bot, db)
        register_compatibility_handlers(
            bot=bot,
            db=db,
            zodiac_service=ZodiacService(),
            biorhythm_calc=BiorhythmCalculator(),
            numerology_calc=NumerologyService(),
            descriptions=CompatibilityDescriptions(),
        )
        register_feedback_handlers(bot=bot, db=db)
        return bot
    except Exception as exc:
        logger.error("Failed to initialise bot: %s", exc)
        return None


@app.route("/", methods=["POST", "OPTIONS"])
@app.route("/api/webhook", methods=["POST", "OPTIONS"])
def webhook():
    if request.method == "OPTIONS":
        return _cors(make_response("", 200))

    if not BOT_TOKEN:
        return _cors(jsonify({"error": "BOT_TOKEN is not configured"})), 500

    body = request.get_data(as_text=True)
    if not body:
        return _cors(jsonify({"error": "Empty request body"})), 400

    try:
        import telebot

        bot = _get_bot()
        if bot is None:
            return _cors(jsonify({"error": "Bot initialisation failed"})), 500

        update = telebot.types.Update.de_json(body)
        bot.process_new_updates([update])
        return _cors(jsonify({"status": "ok"}))
    except Exception as exc:
        logger.error("Error processing webhook update: %s", exc)
        return _cors(jsonify({"error": "Internal error"})), 500
