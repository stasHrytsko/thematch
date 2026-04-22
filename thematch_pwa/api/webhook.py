import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from flask import Flask, request, jsonify

from utils import get_logger, add_cors, cors_preflight

logger = get_logger(__name__)
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")


@app.route("/", methods=["POST", "OPTIONS"])
@app.route("/api/webhook", methods=["POST", "OPTIONS"])
def webhook():
    if request.method == "OPTIONS":
        return cors_preflight("POST, OPTIONS")

    if not BOT_TOKEN:
        return add_cors(
            jsonify({"error": "BOT_TOKEN is not configured"}), "POST, OPTIONS"
        ), 500

    body = request.get_data(as_text=True)
    if not body:
        return add_cors(jsonify({"error": "Empty request body"}), "POST, OPTIONS"), 400

    db = None
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

        update = telebot.types.Update.de_json(body)
        bot.process_new_updates([update])
        return add_cors(jsonify({"status": "ok"}), "POST, OPTIONS")
    except Exception as exc:
        logger.error("Error processing webhook update: %s", exc)
        return add_cors(jsonify({"error": "Internal error"}), "POST, OPTIONS"), 500
    finally:
        if db is not None:
            db.close()
