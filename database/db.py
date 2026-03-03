# database/db.py
import sqlite3
import logging
from typing import Optional

from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __del__(self):        # <-- СЮДА (после строки 11)
        """Закрытие соединения при удалении объекта"""
        if hasattr(self, 'conn'):
            self.conn.close()

    def __init__(self):
        """Инициализация БД"""
        self.conn = sqlite3.connect('thematch.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        """Создание базовых таблиц"""
        with self.conn:
            self.conn.executescript('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    free_checks INTEGER DEFAULT 10,
                    paid_checks INTEGER DEFAULT 0,
                    birth_date DATE
                );

                CREATE TABLE IF NOT EXISTS checks_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date1 TEXT NOT NULL,
                    date2 TEXT NOT NULL,
                    compatibility_score REAL,
                    check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                                    
            ''')

    def get_user(self, user_id):
        """Получение пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

    def create_user(self, user_id, username):
        """Создание пользователя"""
        try:
            with self.conn:
                self.conn.execute(
                    'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                    (user_id, username)
                )
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка создания пользователя: {e}")
            return False

    def update_checks_count(self, user_id, is_free=True):
        """Обновление счетчика проверок"""
        try:
            with self.conn:
                field = 'free_checks' if is_free else 'paid_checks'
                self.conn.execute(
                    f'UPDATE users SET {field} = {field} - 1 WHERE user_id = ? AND {field} > 0',
                    (user_id,)
                )
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления проверок: {e}")
            return False
        
    def add_check_history(self, user_id, date1, date2, compatibility_score):
        """Сохранение результата проверки"""
        try:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO checks_history 
                    (user_id, date1, date2, compatibility_score) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, date1, date2, compatibility_score))
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка сохранения проверки: {e}")
            return False

    def update_user_birth_date(self, user_id: int, birth_date: datetime) -> bool:
        """Обновляет дату рождения пользователя"""
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE users SET birth_date = ? WHERE user_id = ?",
                    (birth_date.strftime("%Y-%m-%d"), user_id)
                )
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления даты рождения: {e}")
            return False

    def get_user_birth_date(self, user_id: int) -> Optional[datetime]:
        """Получает сохраненную дату рождения пользователя"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT birth_date FROM users WHERE user_id = ?", 
                (user_id,)
            )
            result = cursor.fetchone()
            if result and result['birth_date']:
                return datetime.strptime(result['birth_date'], "%Y-%m-%d")
            return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения даты рождения: {e}")
            return None 
    
    def save_feedback(self, user_id: int, text: str) -> bool:
        """Сохранение отзыва пользователя"""
        try:
            with self.conn:
                self.conn.execute(
                    'INSERT INTO feedback (user_id, text) VALUES (?, ?)',
                    (user_id, text)
                )
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка сохранения отзыва: {e}")
            return False
            