# Основные библиотеки
import os
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# Telegram бот
import telebot
from telebot import types
from telebot import types, apihelper  # добавим apihelper

# Импорт наших модулей
from handlers.compatibility import register_compatibility_handlers
from handlers.start import register_start_handlers
from database.db import Database
from services import ZodiacService, BiorhythmCalculator, NumerologyService
from services.descriptions import CompatibilityDescriptions 
from handlers.feedback import register_feedback_handlers

# Базовое логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка наличия токена
TOKEN = os.getenv('BOT_TOKEN', "7919885602:AAGjt6IuXr8mQx1Fboyf3AE0WkA632ywwB0")

if not TOKEN:
    logger.critical("Bot token not found in environment variables!")
    raise ValueError("BOT_TOKEN environment variable is required")

# Инициализация бота и глобальных переменных
bot = telebot.TeleBot(TOKEN)
user_data = {
    'sessions': defaultdict(dict),
    'temp_data': defaultdict(dict),
    'last_action': defaultdict(lambda: datetime.now())
}

# Инициализация сервисов
db = Database()
zodiac_service = ZodiacService()
biorhythm_calc = BiorhythmCalculator()
numerology_calc = NumerologyService ()
descriptions = CompatibilityDescriptions() 

# Точка входа для PythonAnywhere
def application(env, start_response):
    try:
        # Добавить флаг инициализации чтобы не вызывать initialize_handlers() при каждом запросе
        if not hasattr(application, 'is_initialized'):
            initialize_handlers()
            application.is_initialized = True
            
        start_response('200 OK', [('Content-Type', 'text/html')])
        status = "Active" if bot.get_me() else "Inactive"
        return [f"Bot is running. Status: {status}".encode()]
    except Exception as e:
        logger.error(f"WSGI error: {e}")
        start_response('500 Internal Server Error', [('Content-Type', 'text/html')])
        return [b"Bot error occurred"]

# Настройка прокси для PythonAnywhere
if 'PYTHONANYWHERE_DOMAIN' in os.environ:
    apihelper.proxy = {
        'https': 'http://proxy.server:3128'
    }
    apihelper.RETRY_ON_ERROR = True
    apihelper.CONNECT_TIMEOUT = 30

def cleanup_user_data(max_age_hours=24):
    """Очищает старые данные пользователей"""
    current_time = datetime.now()
    for data_dict in [user_data['sessions'], user_data['temp_data']]:
        expired = [
            user_id for user_id, data in data_dict.items()
            if (current_time - user_data['last_action'][user_id]).total_seconds() > max_age_hours * 3600
        ]
        for user_id in expired:
            data_dict.pop(user_id, None)
            user_data['last_action'].pop(user_id, None)
    logger.info(f"Очищено {len(expired)} старых сессий")

def initialize_handlers():
    try:
        register_start_handlers(bot, db)
        register_compatibility_handlers(
            bot=bot, 
            db=db,
            zodiac_service=zodiac_service, 
            biorhythm_calc=biorhythm_calc, 
            numerology_calc=numerology_calc,
            descriptions=descriptions
        )
        # Добавить регистрацию feedback
        register_feedback_handlers(bot=bot, db=db)
        logger.info("Обработчики команд успешно зарегистрированы")
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков: {e}")
        raise

def run_bot():
    try:
        initialize_handlers()
        logger.info("Бот успешно запущен и готов к работе!")
        
        cleanup_user_data()  # Начальная очистка
        
        bot.infinity_polling(
            timeout=60, 
            long_polling_timeout=30,
            skip_pending=True
        )

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        raise

# точка входа
if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
    finally:
        cleanup_user_data()