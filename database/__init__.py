"""
Модуль для работы с базой данных MatchAI бота.
Содержит основные классы и функции для взаимодействия с SQLite.

Основные компоненты:
- Database: Основной класс для работы с БД
- DatabaseError: Кастомные исключения для обработки ошибок БД

Пример использования:
    from database.db import Database
    
    db = Database()
    user = db.get_user(user_id)
"""

from database.db import Database

__version__ = '0.1.0'
__author__ = 'MatchAI Team'

# Публичное API модуля
__all__ = ['Database']

# В будущем можно добавить:
# - Фабрику для создания подключений
# - Кастомные исключения
# - Константы и конфигурацию
# - Миграции