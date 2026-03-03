from telebot import TeleBot, types
import logging

logger = logging.getLogger(__name__)

# Константы
ADMIN_ID = 952754820

def register_feedback_handlers(bot: TeleBot, db):
    @bot.message_handler(func=lambda message: message.text == "📝 Оставить отзыв" or message.text == "/feedback")
    def feedback_start(message):
        logger.info(f"Feedback started by user {message.from_user.id}")
        msg = bot.reply_to(
            message,
            "Пожалуйста, напишите ваш отзыв или предложение:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_feedback)

    def process_feedback(message):
        try:
            user_id = message.from_user.id
            feedback_text = message.text
            logger.info(f"Processing feedback from user {user_id}")

            # Добавляем логирование перед сохранением
            logger.info(f"Attempting to save feedback: {feedback_text[:50]}...")
            
            save_result = db.save_feedback(user_id, feedback_text)
            
            # Логируем результат сохранения
            if save_result:
                logger.info(f"Feedback successfully saved for user {user_id}")
            else:
                logger.error(f"Failed to save feedback for user {user_id}")
                raise Exception("Failed to save feedback")

            # Отправка админу
            try:
                bot.send_message(
                    ADMIN_ID,
                    f"Новый отзыв от пользователя {user_id}:\n\n{feedback_text}"
                )
                logger.info(f"Feedback notification sent to admin")
            except Exception as e:
                logger.error(f"Failed to send feedback to admin: {e}")

            # Возвращаем в главное меню
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                types.KeyboardButton("🔮 Проверить совместимость"),
                types.KeyboardButton("📝 Оставить отзыв")
            )
            
            bot.reply_to(
                message,
                "Спасибо за ваш отзыв! Мы обязательно учтем его в работе.",
                reply_markup=markup
            )
            logger.info(f"Feedback process completed for user {user_id}")

        except Exception as e:
            logger.error(f"Error in process_feedback: {e}")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                types.KeyboardButton("🔮 Проверить совместимость"),
                types.KeyboardButton("📝 Оставить отзыв")
            )
            bot.reply_to(
                message,
                "Произошла ошибка при сохранении отзыва. Пожалуйста, попробуйте позже.",
                reply_markup=markup
            )