# Основные библиотеки
import os
import psutil
import logging
import sys
import time
import random
import signal
from collections import defaultdict
from datetime import datetime, timedelta

# Telegram бот
import telebot
from telebot import types

# Импорт наших модулей
from handlers.compatibility import register_compatibility_handlers
from handlers.start import register_start_handlers
from database.db import Database
from services import ZodiacService, BiorhythmCalculator, NumerologyCalculator
from services.descriptions import CompatibilityDescriptions 

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Проверка наличия токена
TOKEN = os.getenv('BOT_TOKEN')
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
numerology_calc = NumerologyCalculator()
descriptions = CompatibilityDescriptions() 
descriptions = CompatibilityDescriptions()

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
    """Инициализация обработчиков команд"""
    try:
        # Регистрируем обработчики
        register_start_handlers(bot, db)
        register_compatibility_handlers(
            bot=bot, 
            db=db,  # добавить db
            zodiac_service=zodiac_service, 
            biorhythm_calc=biorhythm_calc, 
            numerology_calc=numerology_calc,
            descriptions=descriptions  # это был недостающий аргумент
        )
        logger.info("Обработчики команд успешно зарегистрированы")
    except Exception as e:
        logger.error(f"Ошибка при регистрации обработчиков: {e}")
        raise

def signal_handler(signum, frame):
    """Обработка сигналов завершения"""
    logger.info(f"Получен сигнал завершения {signum}")
    cleanup_user_data()
    if os.path.exists('bot.lock'):
        os.remove('bot.lock')
        logger.info("Lock-файл очищен")
    sys.exit(0)

def run_bot():
    """Основная функция запуска бота"""
    try:
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Инициализируем обработчики команд
        initialize_handlers()
        
        logger.info("Бот успешно запущен и готов к работе!")

        # Основной цикл
        while True:
            try:
                # Периодическая очистка старых данных
                cleanup_user_data()
                
                # Запуск бота
                bot.infinity_polling(timeout=60, long_polling_timeout=30)
                
            except Exception as e:
                logger.error(f"Ошибка в работе бота: {e}")
                time.sleep(5)  # Пауза перед повторным запуском

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        raise

if __name__ == "__main__":
    # Проверка на уже запущенный экземпляр
    if os.path.exists('bot.lock'):
        logger.error("Бот уже запущен. Удалите 'bot.lock', если это не так.")
        sys.exit(1)

    try:
        # Создаем lock-файл
        with open('bot.lock', 'w') as lock_file:
            lock_file.write(str(os.getpid()))
        logger.info("Lock-файл создан")

        # Запускаем бота
        run_bot()

    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        raise
    finally:
        # Очистка при завершении
        cleanup_user_data()
        if os.path.exists('bot.lock'):
            os.remove('bot.lock')
            logger.info("Lock-файл очищен")