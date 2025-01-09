# Базовые команды
from telebot import TeleBot, types
from datetime import datetime
from database.db import Database
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def register_start_handlers(bot: TeleBot, db: Database):
    register_save_birthday_handler(bot, db)
    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = message.from_user.id
        username = message.from_user.username
        
        # Проверяем/создаем пользователя
        user = db.get_user(user_id)
        if not user:
            db.create_user(user_id, username)
            
        # Создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        check_compatibility = types.KeyboardButton("🔮 Проверить совместимость")
        markup.add(check_compatibility)

        welcome_message = (
            f"Привет, {message.from_user.first_name}! 👋\n\n"
            "AI бот для расчёта совместимости.\n\n"
            "🎯 Я анализирую совместимость пар на основе:\n"
            "• Гороскопа (знаки зодиака и их стихии)\n"
            "• Биоритмов (7 основных биоритмических циклов)\n"
            "• Нумерологии (числа судьбы и их взаимодействие)\n\n"
            "🚀 Жми '🔮 Проверить совместимость' чтобы начать анализ!\n\n"
            "Доступные команды:\n"
            "/help - помощь и описание команд\n"
            "/about - информация о боте"
        )
        bot.reply_to(message, welcome_message, reply_markup=markup)

    @bot.message_handler(commands=['help'])
    def help_command(message):
        help_text = (
            "📱 Основные команды:\n"
            "• /start - Начать работу\n"
            "• /help - Показать это сообщение\n"
            "• /about - Информация о боте\n\n"
            "🔍 Как проверить совместимость:\n"
            "1. Нажми '🔮 Проверить совместимость'\n"
            "2. Введи свою дату рождения\n"
            "3. Введи дату рождения партнера\n"
            "4. Получи анализ!"
        )
        bot.reply_to(message, help_text)

    @bot.message_handler(commands=['about'])
    def about_command(message):
        about_text = (
            "ℹ️ О боте MatchAI\n\n"
            "Я - твой персональный астрологический помощник.\n"
            "Анализирую совместимость по:\n"
            "• Знакам зодиака и их стихиям\n"
            "• 7 основным биоритмам\n"
            "• Нумерологическим расчетам\n\n"
            "🔒 Твои данные в безопасности!\n"
            "Я использую их только для расчетов.\n\n"
            "💾 Ты можешь сохранить свою дату рождения\n"
            "командой /save_birthday"
        )
        bot.reply_to(message, about_text)

def register_save_birthday_handler(bot: TeleBot, db: Database):
    @bot.message_handler(commands=['save_birthday'])
    def save_birthday_command(message):
        """Запускает процесс сохранения даты рождения"""
        msg = bot.reply_to(
            message,
            "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990"
        )
        bot.register_next_step_handler(msg, process_save_birthday)

    def process_save_birthday(message):
        """Обрабатывает введенную дату рождения"""
        try:
            user_id = message.from_user.id
            date_text = message.text.strip()
            
            try:
                birth_date = datetime.strptime(date_text, "%d.%m.%Y")
                
                if birth_date > datetime.now():
                    raise ValueError("Дата не может быть в будущем")
                if birth_date.year < 1900:
                    raise ValueError("Дата слишком давняя")
                    
            except ValueError as e:
                bot.reply_to(
                    message,
                    "Неверный формат даты. Используйте ДД.ММ.ГГГГ\nНапример: 25.12.1990"
                )
                return
                
            # Сохраняем в БД
            try:
                db.update_user_birth_date(user_id, birth_date)
                bot.reply_to(
                    message,
                    f"✅ Дата рождения {birth_date.strftime('%d.%m.%Y')} успешно сохранена!"
                )
            except Exception as e:
                logger.error(f"Ошибка сохранения даты в БД: {e}")
                bot.reply_to(
                    message,
                    "Произошла ошибка при сохранении даты. Попробуйте позже."
                )
                
        except Exception as e:
            logger.error(f"Ошибка в process_save_birthday: {e}")
            bot.reply_to(
                message,
                "Произошла ошибка. Попробуйте еще раз или позже."
            )