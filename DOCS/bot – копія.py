# Основные библиотеки
import os
import psutil
import logging
import sys
import time
import random
import signal

from datetime import datetime

from collections import defaultdict
from datetime import datetime, timedelta

# Храним время последнего запроса пользователя
last_request = defaultdict(datetime.now)
COOLDOWN = 2  # секунды между запросами

# Telegram бот
import telebot
from telebot import types

# База данных
import sqlite3

# Наши модули
import services.zodiac as zodiac
from services.descriptions import CompatibilityDescriptions

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),  # Логи в файл
        logging.StreamHandler()          # Логи в консоль
    ]
)
logger = logging.getLogger(__name__)

# Проверка наличия токена
TOKEN = os.getenv('BOT_TOKEN', "7919885602:AAGjt6IuXr8mQx1Fboyf3AE0WkA632ywwB0")
if not TOKEN:
    logger.critical("Bot token not found in environment variables!")
    raise ValueError("BOT_TOKEN environment variable is required")

###### База данных - временно используем in-memory SQLite
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///:memory:')

# Инициализация компонентов
try:
   # Инициализация бота и описаний
   bot = telebot.TeleBot(TOKEN)
   descriptions = CompatibilityDescriptions()
   
   # Хранилище данных пользователей
   user_data = {
        'sessions': {},       # Активные сессии проверки совместимости
        'temp_data': {},      # Временные данные во время диалога
        'last_action': {}     # Последнее действие пользователя
   }

   def cleanup_old_sessions():
       current_time = datetime.now()
       expired = [user_id for user_id, session in user_data['sessions'].items() 
                 if (current_time - session['updated_at']).total_seconds() > 3600]
       for user_id in expired:
           user_data['sessions'].pop(user_id, None)
           
   logger.info("Компоненты инициализированы")

except Exception as e:
   logger.critical(f"Ошибка инициализации: {e}")
   raise

def validate_date(date_str: str) -> tuple[bool, str, datetime | None]:
    """
    Проверяет корректность даты
    
    Args:
        date_str: Строка с датой в формате ДД.ММ.ГГГГ
        
    Returns:
        tuple: (успех, сообщение об ошибке, объект datetime если успех)
    """
    try:
        # Проверяем формат
        if not date_str or len(date_str.split('.')) != 3:
            return False, "Неверный формат даты. Используйте ДД.ММ.ГГГГ", None
            
        # Пробуем преобразовать в datetime
        birth_date = datetime.strptime(date_str, "%d.%m.%Y")
        
        # Проверяем, не в будущем ли дата
        if birth_date > datetime.now():
            return False, "Дата не может быть в будущем", None
            
        # Проверяем, не слишком ли старая дата
        if birth_date.year < 1900:
            return False, "Дата слишком давняя", None
            
        return True, "", birth_date
        
    except ValueError:
        return False, "Неверный формат даты или дата не существует", None

# Initialize database
class Database:
    def __init__(self):
        """Инициализация подключения к базе данных"""
        try:
            db_path = os.path.join(os.path.dirname(__file__), 'thematch.db')
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.create_tables()
            self.migrate_database()
            logger.info("База данных успешно инициализирована")
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    def __enter__(self):
        """Контекстный менеджер для безопасной работы с БД"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие соединения при выходе из контекста"""
        self.conn.close()

    def __del__(self):
        """Деструктор для закрытия соединения"""
        if hasattr(self, 'conn'):
            self.conn.close()
            logger.info("Соединение с БД закрыто")

    def create_tables(self):
        """Создание необходимых таблиц в БД"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                free_checks INTEGER DEFAULT 10,
                paid_checks INTEGER DEFAULT 0,
                birth_date DATE
            )
            ''')

            # Таблица истории проверок
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS checks_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date1 TEXT NOT NULL,
                date2 TEXT NOT NULL,
                compatibility_score REAL,
                check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')

            # Индексы
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_checks_user_id ON checks_history(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_checks_date ON checks_history(check_date)')

            self.conn.commit()
            logger.info("Таблицы БД успешно созданы")
        except sqlite3.Error as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise

    def migrate_database(self):
        """Добавляет новые поля в существующую базу данных"""
        try:
            cursor = self.conn.cursor()
            # Проверяем, есть ли колонка birth_date
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'birth_date' not in columns:
                cursor.execute('''
                    ALTER TABLE users
                    ADD COLUMN birth_date DATE;
                ''')
                self.conn.commit()
                logger.info("Миграция базы данных выполнена успешно")
        except sqlite3.Error as e:
            logger.error(f"Ошибка миграции базы данных: {e}")
            raise

    def create_user(self, user_id, username):
        """Создание нового пользователя в базе данных"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (user_id, username, free_checks, paid_checks) 
                VALUES (?, ?, 10, 0)
            ''', (user_id, username))
            self.conn.commit()
            logger.info(f"Создан новый пользователь: {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка создания пользователя {user_id}: {e}")
            return False

    def get_user(self, user_id):
        """Получение информации о пользователе"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT 
                    user_id,
                    username,
                    free_checks,
                    paid_checks,
                    birth_date
                FROM users 
                WHERE user_id = ?
            ''', (user_id,))
            return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения пользователя {user_id}: {e}")
            return None

    def get_user_birth_date(self, user_id):
        """Получает дату рождения пользователя из базы данных"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''SELECT birth_date FROM users WHERE user_id = ?''', (user_id,))
            result = cursor.fetchone()
            if result and result['birth_date']:
                # Преобразуем SQL-дату с временем в ДД.ММ.ГГГГ
                birth_date = datetime.strptime(result['birth_date'], "%Y-%m-%d %H:%M:%S")
                return birth_date.strftime("%d.%m.%Y")
            return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения даты рождения пользователя {user_id}: {e}")
            return None

    def update_checks_count(self, user_id, is_free=True):
        """Обновление количества доступных проверок"""
        try:
            cursor = self.conn.cursor()
            # Проверяем наличие проверок перед обновлением
            cursor.execute(
                'SELECT free_checks, paid_checks FROM users WHERE user_id = ?',
                (user_id,)
            )
            checks = cursor.fetchone()
            if not checks:
                logger.error(f"Пользователь {user_id} не найден")
                return False

            if is_free and checks['free_checks'] <= 0:
                logger.warning(f"У пользователя {user_id} закончились бесплатные проверки")
                return False

            if not is_free and checks['paid_checks'] <= 0:
                logger.warning(f"У пользователя {user_id} закончились платные проверки")
                return False

            # Обновляем счетчик проверок
            update_field = 'free_checks' if is_free else 'paid_checks'
            cursor.execute(
                f'UPDATE users SET {update_field} = {update_field} - 1 WHERE user_id = ?',
                (user_id,)
            )
            self.conn.commit()
            logger.info(f"Обновлено количество проверок для пользователя {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления проверок для пользователя {user_id}: {e}")
            self.conn.rollback()
            return False

    def add_check_history(self, user_id, date1, date2, compatibility_score):
        """Добавление записи в историю проверок"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO checks_history 
                    (user_id, date1, date2, compatibility_score) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, date1, date2, compatibility_score))
            self.conn.commit()
            logger.info(f"Добавлена запись в историю проверок для пользователя {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления в историю: {e}")
            self.conn.rollback()
            return False
  
    def check_database_structure():
        """Проверяет структуру таблицы users"""
        try:
            with db.conn:
                cursor = db.conn.cursor()
                cursor.execute("PRAGMA table_info(users)")
                columns = cursor.fetchall()
                logger.info(f"Структура таблицы users: {columns}")
                
                # Проверяем наличие колонки birth_date
                has_birth_date = any(col[1] == 'birth_date' for col in columns)
                logger.info(f"Колонка birth_date существует: {has_birth_date}")
                
                return has_birth_date
        except Exception as e:
            logger.error(f"Ошибка проверки структуры БД: {e}")
            return False

def validate_date(date_str: str) -> tuple[bool, str, datetime | None]:
    """
    Проверяет корректность даты
    
    Args:
        date_str: Строка с датой в формате ДД.ММ.ГГГГ
        
    Returns:
        tuple: (успех, сообщение об ошибке, объект datetime если успех)
    """
    try:
        # Проверяем формат
        if not date_str or len(date_str.split('.')) != 3:
            return False, "Неверный формат даты. Используйте ДД.ММ.ГГГГ", None
            
        # Пробуем преобразовать в datetime
        birth_date = datetime.strptime(date_str, "%d.%m.%Y")
        
        # Проверяем, не в будущем ли дата
        if birth_date > datetime.now():
            return False, "Дата не может быть в будущем", None
            
        # Проверяем, не слишком ли старая дата
        if birth_date.year < 1900:
            return False, "Дата слишком давняя", None
            
        return True, "", birth_date
        
    except ValueError:
        return False, "Неверный формат даты или дата не существует", None
                
@bot.message_handler(commands=['check_compatibility'])
def request_birth_date_or_use_saved(message):
    """
    Проверяет, есть ли сохранённая дата рождения.
    Если есть, использует её, иначе запрашивает ввод.
    """
    try:
        user_id = message.from_user.id
        saved_birth_date = db.get_user_birth_date(user_id)

        if saved_birth_date:
            bot.reply_to(
                message,
                f"У вас уже сохранена дата рождения: {saved_birth_date}.\n"
                "Хотите использовать её или ввести новую?",
                reply_markup=create_date_choice_keyboard()
            )
        else:
            msg = bot.reply_to(
                message,
                "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, process_birth_date)
    except Exception as e:
        logger.error(f"Ошибка в request_birth_date_or_use_saved: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")

def create_date_choice_keyboard():
    """Создает клавиатуру для выбора использования сохраненной даты"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    use_saved = types.KeyboardButton("✅ Использовать сохранённую")
    enter_new = types.KeyboardButton("📝 Ввести новую")
    markup.add(use_saved, enter_new)
    return markup

def start_compatibility_check_with_date(message, birth_date):
    """
    Начинает проверку совместимости с использованием сохранённой даты рождения.
    """
    try:
        user_id = message.from_user.id

        # Преобразуем дату в datetime для работы
        birth_date_obj = datetime.strptime(birth_date, "%d.%m.%Y")

        # Инициализируем сессию пользователя
        user_data['sessions'][user_id] = {
            'step': 'partner_birth_date',
            'data': {'birth_date': birth_date_obj}
        }

        msg = bot.reply_to(
            message,
            "Отлично! Теперь введите дату рождения вашего партнера в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
            reply_markup=types.ReplyKeyboardRemove()
        )

        bot.register_next_step_handler(msg, process_partner_birth_date)
    except Exception as e:
        logger.error(f"Ошибка в start_compatibility_check_with_date: {e}")
        bot.reply_to(
            message, "Произошла ошибка при запуске проверки. Попробуйте снова."
        )         

def create_user(self, user_id, username):
    """Создание нового пользователя в базе данных"""
    try:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users 
            (user_id, username, free_checks, paid_checks) 
            VALUES (?, ?, 10, 0)
        ''', (user_id, username))
        self.conn.commit()
        logger.info(f"Создан новый пользователь: {user_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка создания пользователя {user_id}: {e}")
        return False

def get_user(self, user_id):
    try:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                user_id,
                username,
                free_checks,
                paid_checks,
                birth_date    # Добавить это поле
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        return cursor.fetchone()
    except sqlite3.Error as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {e}")
        return None

def update_checks_count(self, user_id, is_free=True):
    """Обновление количества доступных проверок"""
    try:
        cursor = self.conn.cursor()
        # Проверяем наличие проверок перед обновлением
        cursor.execute(
            "UPDATE users SET birth_date = ? WHERE user_id = ?",
            (birth_date.strftime("%Y-%m-%d %H:%M:%S"), user_id)  # Изменить формат даты
        )
        checks = cursor.fetchone()
        if not checks:
            logger.error(f"Пользователь {user_id} не найден")
            return False

        if is_free and checks['free_checks'] <= 0:
            logger.warning(f"У пользователя {user_id} закончились бесплатные проверки")
            return False

        if not is_free and checks['paid_checks'] <= 0:
            logger.warning(f"У пользователя {user_id} закончились платные проверки")
            return False

        # Обновляем счетчик проверок
        update_field = 'free_checks' if is_free else 'paid_checks'
        cursor.execute(
            f'UPDATE users SET {update_field} = {update_field} - 1 WHERE user_id = ?',
            (user_id,)
        )
        self.conn.commit()
        logger.info(f"Обновлено количество проверок для пользователя {user_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка обновления проверок для пользователя {user_id}: {e}")
        self.conn.rollback()
        return False

def add_check_history(self, user_id, date1, date2, compatibility_score):
    """Добавление записи в историю проверок"""
    try:
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO checks_history 
                (user_id, date1, date2, compatibility_score) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, date1, date2, compatibility_score))
        self.conn.commit()
        logger.info(f"Добавлена запись в историю проверок для пользователя {user_id}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Ошибка добавления в историю: {e}")
        self.conn.rollback()
        return False

# Проверка на множественные запуски бота
class BotInstance:
    def __init__(self, lock_file='bot.lock'):
        self.lock_file_path = lock_file
        # Очищаем lock-файл при создании экземпляра
        if os.path.exists(self.lock_file_path):
            os.remove(self.lock_file_path)
            
    def is_process_running(self, pid):
        """Проверяет, запущен ли процесс с данным PID"""
        try:
            process = psutil.Process(pid)
            return False  # Временно всегда возвращаем False
        except:
            return False
    
    def is_running(self):
        try:
            # Создаем новый lock-файл
            with open(self.lock_file_path, 'w') as f:
                f.write(str(os.getpid()))
            return False
        except Exception as e:
            logging.error(f"Ошибка проверки запуска: {e}")
            return True

    def cleanup(self):
        if os.path.exists(self.lock_file_path):
            os.remove(self.lock_file_path)
# Инициализация компонентов
try:
    # Проверяем, не запущен ли уже бот
    bot_instance = BotInstance()
    if bot_instance.is_running():
        logger.critical("Бот уже запущен в другом процессе")
        sys.exit(1)

    # Инициализируем базу данных
    db = Database()
    logger.info("База данных успешно инициализирована")

except Exception as e:
    logger.critical(f"Ошибка при инициализации: {e}")
    raise

def check_flood(message) -> bool:
    """
    Проверка на флуд
    Returns:
        bool: True если это флуд, False если нет
    """
    user_id = message.from_user.id
    now = datetime.now()
    
    if now - last_request[user_id] < timedelta(seconds=COOLDOWN):
        return True
        
    last_request[user_id] = now
    return False

# Добавляем декоратор для всех команд
def anti_flood(func):
    def wrapper(message):
        if check_flood(message):
            return
        return func(message)
    return wrapper

# Применяем к командам
@bot.message_handler(commands=['start'])
@anti_flood
def start(message):
    """
    Обработчик команды /start
    - Инициализирует пользователя в БД
    - Показывает приветственное сообщение
    - Создает клавиатуру с основными командами
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username

        # Проверяем существование пользователя
        user = db.get_user(user_id)
        if not user:
            success = db.create_user(user_id, username)
            if not success:
                logger.error(f"Не удалось создать пользователя: {user_id}")
                bot.reply_to(message, "Извините, произошла ошибка. Попробуйте позже.")
                return

        # Создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        check_compatibility = types.KeyboardButton("🔮 Проверить совместимость")
        markup.add(check_compatibility)

        # Формируем приветственное сообщение
        welcome_message = (
            f"Привет, {message.from_user.first_name}! 👋\n\n"

            "AI бот для расчёта совместимости.\n\n"
            "🎯 Я анализирую совместимость пар на основе:\n"
            "• Гороскопа (знаки зодиака и их стихии)\n"
            "• Биоритмов (7 основных биоритмических циклов)\n"
            "• Нумерологии (числа судьбы и их взаимодействие)\n\n"
            "Ты получишь подробный анализ с общей оценкой совместимости "
            "и детальной расшифровкой каждого параметра.\n\n"
            "🚀 Жми '🔮 Проверить совместимость' чтобы начать анализ!"
        )

        # Отправляем приветствие
        bot.reply_to(message, welcome_message, reply_markup=markup)
        logger.info(f"Начата сессия для пользователя: {user_id}")

        # Очищаем временные данные пользователя
        if user_id in user_data['sessions']:
            user_data['sessions'].pop(user_id, None)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике start: {e}")
        bot.reply_to(
            message,
            "Извините, произошла ошибка. Попробуйте позже или напишите /start"
        )

@bot.message_handler(commands=['help'])
def help_command(message):
    """
    Обработчик команды /help
    Показывает справочную информацию о командах бота
    """
    try:
        help_text = """
        f"{message.from_user.first_name}, вот что я умею:\n\n"
        "📱 Основные команды:\n"
        "• /start - Начать работу со мной\n"
        "• /help - Увидеть это сообщение\n" 
        "• /about - Узнать больше обо мне\n\n"
        "🔍 Как проверить совместимость:\n"
        "1. Нажми '🔮 Проверить совместимость'\n"
        "2. Введи свою дату рождения\n"
        "3. Введи дату рождения партнера\n"
        "4. Получи подробный персональный анализ!\n\n"
        "У тебя осталось X бесплатных проверок.\n"
        "Если нужна помощь - всегда пиши мне!"

У вас есть Х бесплатных проверок.
        """
        bot.reply_to(message, help_text)
        logger.info(f"Показана справка пользователю {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде help: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")

@bot.message_handler(commands=['about'])
def about_command(message):
    """
    Обработчик команды /about
    Показывает информацию о боте
    """
    try:
        about_text = """
ℹ️ О боте MartchAI

        "Привет! Рад рассказать тебе о себе 🤖\n\n"
        "Я - твой персональный астрологический помощник. Я анализирую:\n"
        "• Вашу совместимость по знакам зодиака\n"
        "• Синхронизацию ваших биоритмов\n"
        "• Нумерологическую совместимость\n\n"
        "🎯 Почему я особенный:\n"
        "• Даю точные и подробные расчёты\n"
        "• Объясняю всё простым языком\n"
        "• Постоянно развиваюсь и обновляююсь\n\n"
        "🔒 Твои данные в безопасности!\n"
        "Я использую их только для расчетов и никогда не передаю третьим лицам.\n\n"
        "Остались вопросы? Пиши моему создателю: @support_username"

📱 Поддержка: @support_username
        """
        bot.reply_to(message, about_text)
        logger.info(f"Показана информация о боте пользователю {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка в команде about: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")

# Добавляем возможность сохранять дату рождения пользователя
@bot.message_handler(commands=['save_birthday'])
def process_birthday_save(message):
    """Сохраняет дату рождения пользователя в базу данных"""
    try:
        user_id = message.from_user.id
        date_text = message.text.strip()
        logger.info(f"Начало сохранения даты рождения для пользователя {user_id}. Введенная дата: {date_text}")

        try:
            birth_date = datetime.strptime(date_text, "%d.%m.%Y")
            logger.info(f"Дата успешно преобразована в datetime: {birth_date}")
            
            current_date = datetime.now()
            if birth_date > current_date:
                logger.warning(f"Попытка ввести будущую дату: {birth_date}")
                raise ValueError("Дата не может быть в будущем")

            if birth_date.year < 1900:
                logger.warning(f"Попытка ввести слишком раннюю дату: {birth_date}")
                raise ValueError("Дата слишком давняя")

        except ValueError as e:
            logger.error(f"Ошибка валидации даты: {e}")
            bot.reply_to(
                message,
                "Неверный формат даты или дата некорректна. Введите дату в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990"
            )
            bot.register_next_step_handler(message, process_birthday_save)
            return

        try:
            with db.conn:
                cursor = db.conn.cursor()
                
                # Проверяем текущее значение
                cursor.execute("SELECT birth_date FROM users WHERE user_id = ?", (user_id,))
                current_value = cursor.fetchone()
                logger.info(f"Текущее значение в БД: {current_value}")
                
                formatted_date = birth_date.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"Подготовленная для сохранения дата: {formatted_date}")
                
                # Обновляем дату
                cursor.execute(
                    "UPDATE users SET birth_date = ? WHERE user_id = ?",
                    (formatted_date, user_id)
                )
                
                # Проверяем, сколько строк было обновлено
                rows_affected = cursor.rowcount
                logger.info(f"Обновлено строк в БД: {rows_affected}")
                
                if rows_affected == 0:
                    logger.warning(f"Пользователь {user_id} не найден, создаем новую запись")
                    cursor.execute(
                        "INSERT INTO users (user_id, birth_date) VALUES (?, ?)",
                        (user_id, formatted_date)
                    )
                
                # Проверяем, что изменения применились
                cursor.execute("SELECT birth_date FROM users WHERE user_id = ?", (user_id,))
                new_value = cursor.fetchone()
                logger.info(f"Новое значение в БД: {new_value}")
                
                db.conn.commit()
                logger.info("Транзакция успешно завершена")

        except Exception as db_error:
            logger.error(f"Ошибка работы с БД: {db_error}", exc_info=True)
            raise

        bot.reply_to(
            message,
            f"✅ Дата рождения {birth_date.strftime('%d.%m.%Y')} успешно сохранена!"
        )
        logger.info(f"Сохранение даты рождения для пользователя {user_id} успешно завершено")

    except Exception as e:
        logger.error(f"Критическая ошибка в process_birthday_save: {e}", exc_info=True)
        bot.reply_to(
            message,
            "❌ Произошла ошибка при сохранении даты рождения. Попробуйте снова позже."
        )

@bot.message_handler(func=lambda message: message.text == "🔮 Проверить совместимость")
def start_compatibility_check(message):
    try:
        user_id = message.from_user.id

        # Очищаем предыдущие данные пользователя если они есть
        user_data['sessions'].pop(user_id, None)
        user_data['temp_data'].pop(user_id, None)

        # Инициализируем сессию пользователя
        user_data['sessions'][user_id] = {
            'step': 'birth_date',
            'data': {}
        }
        
        msg = bot.reply_to(
            message,
            "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Регистрируем следующий шаг
        bot.register_next_step_handler(msg, request_birth_date)
        logger.info(f"Начата проверка совместимости для пользователя: {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в start_compatibility_check: {e}")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("🔮 Проверить совместимость"))
        bot.reply_to(
            message, 
            "Извините, произошла ошибка. Нажмите '🔮 Проверить совместимость' чтобы начать заново.",
            reply_markup=markup
        )

def request_birth_date(message):
    try:
        user_id = message.from_user.id
        
        # Если пользователь хочет исправить дату
        if message.text == "↩️ Ввести дату заново":
            msg = bot.reply_to(
                message,
                "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
            )
            bot.register_next_step_handler(msg, request_birth_date)
            return
            
        date_text = message.text.strip()
        
        try:
            birth_date = datetime.strptime(date_text, "%d.%m.%Y")
            current_date = datetime.now()
            min_date = datetime(1940, 1, 1)
            
            if birth_date > current_date:
                raise ValueError("будущее")
            if birth_date < min_date:
                raise ValueError("прошлое")
                
        except ValueError as e:
            if "будущее" in str(e):
                msg = "Дата не может быть в будущем!"
            elif "прошлое" in str(e):
                msg = "Дата слишком давняя. Укажите дату после 1940 года."
            else:
                msg = "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990"
            
            bot.reply_to(message, msg)
            bot.register_next_step_handler(message, request_birth_date)
            return

        # Создаем клавиатуру с кнопкой подтверждения и исправления
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        confirm = types.KeyboardButton("✅ Подтвердить")
        retry = types.KeyboardButton("↩️ Ввести дату заново")
        markup.add(confirm, retry)
            
        msg = bot.reply_to(
            message,
            f"Вы ввели дату: {birth_date.strftime('%d.%m.%Y')}\nВсё верно?",
            reply_markup=markup
        )
        
        # Сохраняем дату временно
        user_data['temp_data'][user_id] = {'temp_birth_date': birth_date}
        
        bot.register_next_step_handler(msg, confirm_birth_date)
        
    except Exception as e:
        logger.error(f"Ошибка в request_birth_date: {e}")
        return_to_start(message)

def confirm_birth_date(message):
    try:
        user_id = message.from_user.id
        
        if message.text == "↩️ Ввести дату заново":
            msg = bot.reply_to(
                message,
                "Хорошо, введите дату рождения заново в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, request_birth_date)
            return
            
        if message.text == "✅ Подтвердить":
            # Проверяем наличие временных данных
            temp_data = user_data.get('temp_data', {}).get(user_id, {})
            if 'temp_birth_date' not in temp_data:
                logger.error(f"Нет временных данных для пользователя {user_id}")
                bot.reply_to(
                    message,
                    "Произошла ошибка. Попробуйте снова ввести дату рождения."
                )
                return_to_start(message)
                return

            # Получаем сохранённую дату
            birth_date = temp_data['temp_birth_date']
            
            # Сохраняем в сессию
            user_data['sessions'][user_id] = user_data.get('sessions', {}).get(user_id, {})
            user_data['sessions'][user_id]['data'] = user_data['sessions'][user_id].get('data', {})
            user_data['sessions'][user_id]['data']['birth_date'] = birth_date
            user_data['sessions'][user_id]['step'] = 'partner_birth_date'
            
            # Очищаем временные данные
            user_data['temp_data'].pop(user_id, None)
            
            msg = bot.reply_to(
                message,
                "Отлично! Теперь введите дату рождения вашего партнера в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            bot.register_next_step_handler(msg, process_partner_birth_date)
            logger.info(f"Дата рождения пользователя {user_id} подтверждена: {birth_date}")
            
    except Exception as e:
        logger.error(f"Ошибка в confirm_birth_date: {e}")
        return_to_start(message)

def process_partner_birth_date(message):
    try:
        user_id = message.from_user.id
        
        # Если пользователь хочет исправить дату
        if message.text == "↩️ Ввести дату заново":
            msg = bot.reply_to(
                message,
                "Введите дату рождения партнера в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990"
            )
            bot.register_next_step_handler(msg, process_partner_birth_date)
            return
            
        date_text = message.text.strip()
        
        try:
            partner_birth_date = datetime.strptime(date_text, "%d.%m.%Y")
            if partner_birth_date > datetime.now():
                raise ValueError("Дата не может быть в будущем")
            if partner_birth_date.year < 1940:
                raise ValueError("Дата слишком давняя")
                
        except (ValueError, TypeError):
            msg = bot.reply_to(
                message,
                "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990"
            )
            bot.register_next_step_handler(msg, process_partner_birth_date)
            return

        # Создаем клавиатуру с кнопкой подтверждения и исправления
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        confirm = types.KeyboardButton("✅ Подтвердить")
        retry = types.KeyboardButton("↩️ Ввести дату заново")
        markup.add(confirm, retry)
            
        msg = bot.reply_to(
            message,
            f"Дата рождения партнера: {partner_birth_date.strftime('%d.%m.%Y')}\nВсё верно?",
            reply_markup=markup
        )
        
        # Сохраняем дату временно
        user_data['temp_data'][user_id] = {'temp_partner_birth_date': partner_birth_date}
        
        bot.register_next_step_handler(msg, confirm_partner_birth_date)
        
    except Exception as e:
        logger.error(f"Ошибка в process_partner_birth_date: {e}")
        return_to_start(message)

def confirm_partner_birth_date(message):
    try:
        user_id = message.from_user.id
        
        if message.text == "↩️ Ввести дату заново":
            msg = bot.reply_to(
                message,
                "Хорошо, введите дату рождения партнера заново в формате ДД.ММ.ГГГГ\nНапример: 25.12.1990",
                reply_markup=types.ReplyKeyboardRemove()
            )
            bot.register_next_step_handler(msg, process_partner_birth_date)
            return
            
        if message.text == "✅ Подтвердить":
            # Получаем обе даты
            first_date = user_data['sessions'][user_id]['data']['birth_date']
            second_date = user_data['temp_data'][user_id]['temp_partner_birth_date']
            
            # Очищаем временные данные
            user_data['temp_data'].pop(user_id, None)
            
            # Запускаем расчет
            process_compatibility_calculation(message, first_date, second_date)
            
    except Exception as e:
        logger.error(f"Ошибка в confirm_partner_birth_date: {e}")
        return_to_start(message)

@bot.message_handler(commands=['delete_birthday'])
def delete_birthday(message):
    """Удаляет сохраненную дату рождения пользователя"""
    try:
        user_id = message.from_user.id
        
        # Проверяем, есть ли сохраненная дата
        saved_date = db.get_user_birth_date(user_id)
        if not saved_date:
            bot.reply_to(message, "У вас нет сохранённой даты рождения.")
            return
            
        # Создаем клавиатуру для подтверждения
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        yes = types.KeyboardButton("✅ Да, удалить")
        no = types.KeyboardButton("❌ Нет, оставить")
        markup.add(yes, no)
        
        msg = bot.reply_to(
            message,
            f"Вы уверены, что хотите удалить сохранённую дату рождения ({saved_date})?",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, confirm_delete_birthday)
        
    except Exception as e:
        logger.error(f"Ошибка в delete_birthday: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")

def confirm_delete_birthday(message):
    """Подтверждение удаления даты рождения"""
    try:
        if message.text == "✅ Да, удалить":
            user_id = message.from_user.id
            
            # Удаляем дату из базы
            with db.conn:
                cursor = db.conn.cursor()
                cursor.execute(
                    "UPDATE users SET birth_date = NULL WHERE user_id = ?",
                    (user_id,)
                )
            
            bot.reply_to(
                message,
                "Дата рождения успешно удалена!",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            bot.reply_to(
                message,
                "Удаление отменено.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
    except Exception as e:
        logger.error(f"Ошибка в confirm_delete_birthday: {e}")
        bot.reply_to(
            message,
            "Произошла ошибка при удалении даты. Попробуйте позже.",
            reply_markup=types.ReplyKeyboardRemove()
        )

def return_to_start(message):
    """
    Возвращает пользователя к начальному состоянию
    """
    try:
        # Очищаем данные пользователя
        user_id = message.chat.id
        user_data['sessions'].pop(user_id, None)
        user_data['temp_data'].pop(user_id, None)
        
        # Возвращаем начальную клавиатуру
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

def process_compatibility_calculation(message, first_date, second_date):
    """
    Calculates and formats compatibility results
    """
    try:
        # Отправляем сообщение о начале анализа
        processing_msg = bot.reply_to(message, "🔄 Анализирую совместимость...")

        # Имитируем процесс вычислений
        bot.send_chat_action(message.chat.id, 'typing')
        time.sleep(3)

        try:
            # Удаляем сообщение о процессе
            bot.delete_message(message.chat.id, processing_msg.message_id)
        except Exception as e:
            logger.warning(f"Could not delete processing message: {e}")

        # Расчет совместимости
        total_comp, details = zodiac.calculate_zodiac_compatibility(first_date, second_date)
        logger.info(f"Compatibility calculated for user {message.from_user.id}: {total_comp}%")

        # Получаем эмодзи для всех процентов
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
            'higher': descriptions.get_emoji(details['biorhythms']['rhythms']['higher']['compatibility']),
        }

        # Получаем фразу для общей совместимости
        compatibility_phrase = descriptions.get_random_phrase(total_comp, descriptions.GENERAL_COMPATIBILITY_PHRASES)

        # Определяем тип совместимости стихий и получаем фразу
        elements_type = descriptions.get_elements_compatibility_type(details['element1'], details['element2'])
        elements_phrase = random.choice(descriptions.ELEMENTS_COMPATIBILITY_PHRASES[elements_type])

        try:
            # Получаем описания знаков
            sign1_description = descriptions.ZODIAC_DESCRIPTIONS[details['sign1']]
            sign2_description = descriptions.ZODIAC_DESCRIPTIONS[details['sign2']]

            logger.info(f"Sign1: {details['sign1']}")
            logger.info(f"Sign2: {details['sign2']}")
        except KeyError as e:
            logger.error(f"KeyError: {e}")
            logger.info(f"Available signs: {descriptions.ZODIAC_DESCRIPTIONS.keys()}")

        # For testing - no limits
        remaining = "∞"
        checks_type = "тестовых"

        # Форматируем результат
        result_message = f"""
        ✨ Результат анализа совместимости:

        
        Вы: {details['sign1']} ({zodiac.get_sign_name(details['sign1'])})
        Дата рождения: {first_date.strftime('%d.%m.%Y')}
        «{sign1_description}»

        Ваш партнер: {details['sign2']} ({zodiac.get_sign_name(details['sign2'])})
        Дата рождения: {second_date.strftime('%d.%m.%Y')}
        «{sign2_description}»
        
        ---

        🌟 Общая совместимость: {round(total_comp, 1):,.1f}% {main_emoji}
        «{compatibility_phrase}»
        
        ---

        🔯 Зодиакальный анализ:
 
        - Совместимость Знаков: {details['sign2']} + {details['sign1']} = {details['signs_compatibility']:,.1f}% {signs_emoji}
        
        - Совместимость Стихий: {zodiac.ELEMENTS_ICONS[details['element2']]} {details['element2']} + {zodiac.ELEMENTS_ICONS[details['element1']]} {details['element1']} = {details['elements_compatibility']:,.1f}% {elements_emoji}
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

       - Высший: {details['biorhythms']['rhythms']['higher']['compatibility']:,.1f}% {bio_emoji['higher']}
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
        «{descriptions.get_random_phrase(details['numerology']['compatibility'], descriptions.NUMEROLOGY_COMPATIBILITY_PHRASES)}»
        ---
        У вас осталось {remaining} {checks_type} проверок."""

        # Reset keyboard to initial state
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        check_compatibility = types.KeyboardButton("🔮 Проверить совместимость")
        markup.add(check_compatibility)

        bot.reply_to(message, result_message, reply_markup=markup)
        logger.info(f"Results sent to user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error in process_compatibility_calculation: {e}")
        bot.reply_to(
            message,
            "Произошла ошибка при расчете совместимости. Попробуйте начать заново с команды /start"
        )

    from requests.exceptions import ReadTimeout, ConnectionError, RequestException
    import sys
    from datetime import datetime

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}")
    if hasattr(signal_handler, 'bot_instance'):
        logger.info("Cleaning up bot instance...")
        del signal_handler.bot_instance
    sys.exit(0)

def run_bot():
    bot_instance = BotInstance()
    if bot_instance.is_running():
        logger.error("Бот уже запущен")
        return
    logger.info(f"Запуск бота: {datetime.now()}")
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            logger.info("Старт поллинга...")
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=30,
                allowed_updates=["message", "callback_query"],
            )
            
        except Exception as e:
            logger.error(f"Ошибка в работе бота: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # Принудительно очищаем lock-файл при старте
    if os.path.exists('bot.lock'):
        os.remove('bot.lock')
        logger.info("Lock-файл очищен")

    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную")
        bot_instance.cleanup()
    except Exception as e:
        logger.critical(f"Критическая ошибка: {e}")
        bot_instance.cleanup()
        raise