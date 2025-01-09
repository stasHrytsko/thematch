# Логика проверки совместимости
import logging
from datetime import datetime
import random
from telebot import TeleBot, types
from database.db import Database



# Импорты сервисов
from services.zodiac import ZodiacService
from services.biorhythm import BiorhythmCalculator
from services.numerology import NumerologyCalculator
from services.descriptions import CompatibilityDescriptions

logger = logging.getLogger(__name__)


def register_compatibility_handlers(
    bot: TeleBot, 
    db: Database,
    zodiac_service: ZodiacService,
    biorhythm_calc: BiorhythmCalculator,
    numerology_calc: NumerologyCalculator,
    descriptions: CompatibilityDescriptions
):
    user_states = {}

    def cleanup_old_states():
        current_time = datetime.now()
        expired = []
        for user_id in user_states:
            if 'last_activity' in user_states[user_id]:
                if (current_time - user_states[user_id]['last_activity']).total_seconds() > 3600:
                    expired.append(user_id)

        for user_id in expired:
            user_states.pop(user_id, None)
    
    def create_confirm_markup():
        """Создает клавиатуру для подтверждения даты"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("✅ Подтвердить"),
            types.KeyboardButton("↩️ Ввести дату заново")
        )
        return markup

    def validate_date(date_str: str) -> tuple[bool, str, datetime | None]:
        """Проверяет корректность даты"""
        try:
            if not date_str or len(date_str.split('.')) != 3:
                return False, "Неверный формат даты. Используйте ДД.ММ.ГГГГ", None
                
            birth_date = datetime.strptime(date_str, "%d.%m.%Y")
            
            if birth_date > datetime.now():
                return False, "Дата не может быть в будущем", None
                
            if birth_date.year < 1900:
                return False, "Дата слишком давняя", None
                
            return True, "", birth_date
            
        except ValueError:
            return False, "Неверный формат даты или дата не существует", None
        
    def return_to_start(message):
        """Возврат к начальному состоянию"""
        try:
            user_id = message.chat.id
            user_states.pop(user_id, None)
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            check_compatibility = types.KeyboardButton("🔮 Проверить совместимость")
            markup.add(check_compatibility)
            
            bot.send_message(
                message.chat.id,
                "Давайте начнем сначала. Нажмите '🔮 Проверить совместимость'",
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при возврате к началу: {e}")

    @bot.message_handler(func=lambda message: message.text in ["🔮 Проверить совместимость", "✅ Использовать сохраненную", "📝 Ввести новую"])
    def process_date_choice(message):
        try:
            user_id = message.from_user.id

            if message.text == "📝 Ввести новую":
                msg = bot.reply_to(
                    message,
                    "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                bot.register_next_step_handler(msg, process_first_date)
                return

            if message.text == "✅ Использовать сохраненную":
                saved_date = db.get_user_birth_date(user_id)
                if not saved_date:
                    return_to_start(message)
                    return
                    
                # Инициализируем состояние пользователя
                if user_id not in user_states:
                    user_states[user_id] = {
                        'step': 'first_date',
                        'data': {}
                    }
                user_states[user_id]['first_date'] = saved_date
                
                # Сразу переходим к вводу второй даты
                msg = bot.reply_to(
                    message,
                    "Теперь введите дату рождения партнера в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                bot.register_next_step_handler(msg, process_second_date)
                return

            # Если это начальная команда проверки совместимости
            saved_date = db.get_user_birth_date(user_id)
            if saved_date:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(
                    types.KeyboardButton("✅ Использовать сохраненную"),
                    types.KeyboardButton("📝 Ввести новую")
                )
                bot.reply_to(
                    message,
                    f"У вас есть сохранённая дата: {saved_date.strftime('%d.%m.%Y')}\n"
                    "Хотите использовать её или ввести новую?",
                    reply_markup=markup
                )
            else:
                msg = bot.reply_to(
                    message,
                    "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                bot.register_next_step_handler(msg, process_first_date)
                    
        except Exception as e:
            logger.error(f"Ошибка в process_date_choice: {e}")
            return_to_start(message)

    def process_first_date(message):
        try:
            user_id = message.from_user.id
            
            # Инициализируем состояние пользователя если его нет
            if user_id not in user_states:
                user_states[user_id] = {
                    'step': 'first_date',
                    'data': {}
                }

            if message.text == "↩️ Ввести дату заново":
                msg = bot.reply_to(
                    message,
                    "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                )
                bot.register_next_step_handler(msg, process_first_date)
                return
                
            # Добавить эти строки:
            is_valid, error_msg, birth_date = validate_date(message.text.strip())
            if not is_valid:
                msg = bot.reply_to(message, error_msg)
                bot.register_next_step_handler(msg, process_first_date)
                return

            # Сохраняем дату во временное хранилище
            user_states[user_id]['first_date'] = birth_date
            
            # Просим подтверждение и предлагаем сохранить
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            save_date = types.KeyboardButton("💾 Сохранить дату")
            continue_btn = types.KeyboardButton("➡️ Продолжить")
            markup.add(save_date, continue_btn)
            
            msg = bot.reply_to(
                message,
                f"Дата принята: {birth_date.strftime('%d.%m.%Y')}\n"
                "Хотите сохранить эту дату для будущих проверок?",
                reply_markup=markup
            )
            
            user_states[user_id]['temp_date'] = birth_date
            bot.register_next_step_handler(msg, process_date_saving)

        except Exception as e:
            logger.error(f"Ошибка в process_first_date: {e}")
            return_to_start(message)

    def confirm_first_date(message):
        """Подтверждение введенной даты рождения"""
        try:
            user_id = message.from_user.id
            
            if message.text == "↩️ Ввести дату заново":
                msg = bot.reply_to(
                    message,
                    "Хорошо, введите дату рождения заново в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                bot.register_next_step_handler(msg, process_first_date)
                return
                
            if message.text == "✅ Подтвердить":
                # После подтверждения предлагаем сохранить дату
                birth_date = user_states[user_id]['first_date']
                
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                save_date = types.KeyboardButton("💾 Сохранить дату")
                continue_btn = types.KeyboardButton("➡️ Продолжить")
                markup.add(save_date, continue_btn)
                
                msg = bot.reply_to(
                    message,
                    f"Дата принята: {birth_date.strftime('%d.%m.%Y')}\n"
                    "Хотите сохранить эту дату для будущих проверок?",
                    reply_markup=markup
                )
                
                user_states[user_id]['temp_date'] = birth_date
                bot.register_next_step_handler(msg, process_date_saving)
                
        except Exception as e:
            logger.error(f"Ошибка в confirm_first_date: {e}")
            return_to_start(message)

    def process_date_saving(message):
        try:
            user_id = message.from_user.id
            
            if message.text == "💾 Сохранить дату":
                birth_date = user_states[user_id]['temp_date']
                
                if db.update_user_birth_date(user_id, birth_date):
                    bot.reply_to(
                        message,
                        "✅ Дата успешно сохранена!",
                        reply_markup=types.ReplyKeyboardRemove()
                    )
                else:
                    bot.reply_to(
                        message,
                        "❌ Не удалось сохранить дату",
                        reply_markup=types.ReplyKeyboardRemove()
                    )
            
            # В любом случае продолжаем процесс
            msg = bot.reply_to(
                message,
                "Теперь введите дату рождения партнера в формате ДД.ММ.ГГГГ",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, process_second_date)
            
        except Exception as e:
            logger.error(f"Ошибка в process_date_saving: {e}")
            return_to_start(message)

    def process_second_date(message):
        try:
            user_id = message.from_user.id
            
            if message.text == "↩️ Ввести дату заново":
                msg = bot.reply_to(
                    message,
                    "Введите дату рождения партнера в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990"
                )
                bot.register_next_step_handler(msg, process_second_date)
                return

            is_valid, error_msg, birth_date = validate_date(message.text.strip())
            if not is_valid:
                msg = bot.reply_to(message, error_msg)
                bot.register_next_step_handler(msg, process_second_date)
                return

            user_states[user_id]['second_date'] = birth_date
            
            msg = bot.reply_to(
                message,
                f"Дата рождения партнера: {birth_date.strftime('%d.%m.%Y')}\nВсё верно?",
                reply_markup=create_confirm_markup()
            )
            
            user_states[user_id]['step'] = 'confirming_second_date'
            bot.register_next_step_handler(msg, confirm_second_date)
            
        except Exception as e:
            logger.error(f"Ошибка в process_second_date: {e}")
            return_to_start(message)

    def confirm_second_date(message):
        try:
            user_id = message.from_user.id
            
            if message.text == "↩️ Ввести дату заново":
                msg = bot.reply_to(
                    message,
                    "Введите дату рождения партнера заново в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                bot.register_next_step_handler(msg, process_second_date)
                return
                
            if message.text == "✅ Подтвердить":
                first_date = user_states[user_id]['first_date']
                second_date = user_states[user_id]['second_date']
                
                # Запускаем расчет
                process_compatibility_calculation(message, first_date, second_date)
                
                # Очищаем состояние пользователя
                user_states.pop(user_id, None)
                
        except Exception as e:
            logger.error(f"Ошибка в confirm_second_date: {e}")
            return_to_start(message)

    def process_compatibility_calculation(message, first_date, second_date):
        """Расчет и отправка результатов совместимости"""
        try:
            processing_msg = bot.reply_to(message, "🔄 Анализирую совместимость...")
            
            try:
                bot.delete_message(message.chat.id, processing_msg.message_id)
            except Exception as e:
                logger.warning(f"Could not delete processing message: {e}")

            # Расчет зодиакальной совместимости
            zodiac_comp, zodiac_details = zodiac_service.calculate_zodiac_compatibility(
                first_date, 
                second_date
            )
            
            # Расчет биоритмов
            bio_comp, bio_details = biorhythm_calc.calculate_compatibility(
                first_date,
                second_date
            )
            
            # Расчет нумерологии
            num_comp, num_details = numerology_calc.calculate_compatibility(
                first_date,
                second_date
            )

            # Объединяем все детали
            details = {
                **zodiac_details,
                'biorhythms': bio_details,
                'numerology': num_details
            }

            # Общая совместимость (средневзвешенное значение)
            total_comp = (
                zodiac_comp * 0.4 +  # 40% вес
                bio_comp * 0.35 +    # 35% вес
                num_comp * 0.25      # 25% вес
            )

            # Формируем результат
            result = format_compatibility_result(
                total_comp, 
                details, 
                first_date, 
                second_date,
                zodiac_service,
                descriptions
            )

            # Возвращаем клавиатуру в начальное состояние
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            check_compatibility = types.KeyboardButton("🔮 Проверить совместимость")
            markup.add(check_compatibility)

            bot.reply_to(message, result, reply_markup=markup)
            logger.info(f"Results sent to user {message.from_user.id}")

        except Exception as e:
            logger.error(f"Error in process_compatibility_calculation: {e}")
            bot.reply_to(
                message,
                "Произошла ошибка при расчете совместимости. Попробуйте начать заново с команды /start"
            )

    def format_compatibility_result(
        total_comp: float,
        details: dict,
        first_date: datetime,
        second_date: datetime,
        zodiac_service: ZodiacService,
        descriptions: CompatibilityDescriptions
    ) -> str:
        try:
            # Получаем эмодзи для всех процентов через сервис descriptions
            main_emoji = descriptions.get_emoji(total_comp)
            signs_emoji = descriptions.get_emoji(details['signs_compatibility'])
            elements_emoji = descriptions.get_emoji(details['elements_compatibility'])
            
            bio_emoji = {
                'physical': descriptions.get_emoji(details['biorhythms']['rhythms']['physical']['compatibility']),
                'emotional': descriptions.get_emoji(details['biorhythms']['rhythms']['emotional']['compatibility']),
                'intellectual': descriptions.get_emoji(details['biorhythms']['rhythms']['intellectual']['compatibility']),
                'heart': descriptions.get_emoji(details['biorhythms']['rhythms']['heart']['compatibility']),
                'creative': descriptions.get_emoji(details['biorhythms']['rhythms']['creative']['compatibility']),
                'intuitive': descriptions.get_emoji(details['biorhythms']['rhythms']['intuitive']['compatibility']),
                'higher': descriptions.get_emoji(details['biorhythms']['rhythms']['higher']['compatibility'])
            }

            # Получаем фразы через сервис descriptions
            compatibility_phrase = descriptions.get_random_phrase(
                total_comp, 
                descriptions.GENERAL_COMPATIBILITY_PHRASES
            )
            
            elements_type = descriptions.get_elements_compatibility_type(
                details['element1'], 
                details['element2']
            )
            elements_phrase = random.choice(
                descriptions.ELEMENTS_COMPATIBILITY_PHRASES[elements_type]
            )

            # Формируем результат
            result = f"""✨ Результат анализа совместимости:

Вы: {details['sign1']} ({zodiac_service.get_sign_name(details['sign1'])})
Дата рождения: {first_date.strftime('%d.%m.%Y')}
«{descriptions.ZODIAC_DESCRIPTIONS[details['sign1']]}»

Ваш партнер: {details['sign2']} ({zodiac_service.get_sign_name(details['sign2'])})
Дата рождения: {second_date.strftime('%d.%m.%Y')}
«{descriptions.ZODIAC_DESCRIPTIONS[details['sign2']]}»

---

🌟 Общая совместимость: {round(total_comp, 1):,.1f}% {main_emoji}
«{compatibility_phrase}»

---

🔯 Зодиакальный анализ:

- Совместимость Знаков: {details['sign2']} + {details['sign1']} = {details['signs_compatibility']:,.1f}% {signs_emoji}

- Совместимость Стихий: {zodiac_service.ELEMENTS_ICONS[details['element2']]} {details['element2']} + {zodiac_service.ELEMENTS_ICONS[details['element1']]} {details['element1']} = {details['elements_compatibility']:,.1f}% {elements_emoji}
«{elements_phrase}»

---

💫 Биоритмы:

Физический: {details['biorhythms']['rhythms']['physical']['compatibility']:,.1f}% {bio_emoji['physical']}
«{descriptions.get_biorhythm_description('physical', details['biorhythms']['rhythms']['physical']['compatibility'])}»

Эмоциональный: {details['biorhythms']['rhythms']['emotional']['compatibility']:,.1f}% {bio_emoji['emotional']}
«{descriptions.get_biorhythm_description('emotional', details['biorhythms']['rhythms']['emotional']['compatibility'])}»

Интеллектуальный: {details['biorhythms']['rhythms']['intellectual']['compatibility']:,.1f}% {bio_emoji['intellectual']}
«{descriptions.get_biorhythm_description('intellectual', details['biorhythms']['rhythms']['intellectual']['compatibility'])}»

Сердечный: {details['biorhythms']['rhythms']['heart']['compatibility']:,.1f}% {bio_emoji['heart']}
«{descriptions.get_biorhythm_description('heart', details['biorhythms']['rhythms']['heart']['compatibility'])}»

Творческий: {details['biorhythms']['rhythms']['creative']['compatibility']:,.1f}% {bio_emoji['creative']}
«{descriptions.get_biorhythm_description('creative', details['biorhythms']['rhythms']['creative']['compatibility'])}»

Интуитивный: {details['biorhythms']['rhythms']['intuitive']['compatibility']:,.1f}% {bio_emoji['intuitive']}
«{descriptions.get_biorhythm_description('intuitive', details['biorhythms']['rhythms']['intuitive']['compatibility'])}»

Высший: {details['biorhythms']['rhythms']['higher']['compatibility']:,.1f}% {bio_emoji['higher']}
«{descriptions.get_biorhythm_description('higher', details['biorhythms']['rhythms']['higher']['compatibility'])}»

Общая совместимость биоритмов: {details['biorhythms']['total']:,.1f}% {descriptions.get_emoji(details['biorhythms']['total'])}
«{descriptions.get_biorhythm_description('total', details['biorhythms']['total'])}»

---

🔢 Числа судьбы:

Ваше число: {details['numerology']['number1']}
«{descriptions.NUMEROLOGY_DESCRIPTIONS[details['numerology']['number1']]}»

Число партнера: {details['numerology']['number2']}
«{descriptions.NUMEROLOGY_DESCRIPTIONS[details['numerology']['number2']]}»

Совместимость чисел: {details['numerology']['compatibility']:,.1f}% {descriptions.get_emoji(details['numerology']['compatibility'])}
«{descriptions.get_random_phrase(details['numerology']['compatibility'], descriptions.NUMEROLOGY_COMPATIBILITY_PHRASES)}»"""

            return result

        except Exception as e:
            logger.error(f"Error in format_compatibility_result: {e}")
            return "Ошибка форматирования результата"
        
    # Регистрируем обработчики
    handlers = {
        'check_compatibility': {
            'function': process_date_choice,
            'filters': {'func': lambda message: message.text == "🔮 Проверить совместимость"}
        },
        'use_saved_date': {  # Добавить этот обработчик
            'function': process_date_choice,
            'filters': {'func': lambda message: message.text in ["✅ Использовать сохраненную", "📝 Ввести новую"]}
        }
    }

            # Регистрируем каждый обработчик
    for name, handler in handlers.items():
        try:
            bot.register_message_handler(
                handler['function'],
                **handler.get('filters', {})
            )
            logger.info(f"Зарегистрирован обработчик: {name}")
        except Exception as e:
            logger.error(f"Ошибка регистрации обработчика {name}: {e}")
            raise

    return {
        'process_first_date': process_first_date,
        'confirm_first_date': confirm_first_date,
        'process_second_date': process_second_date,
        'confirm_second_date': confirm_second_date
    }