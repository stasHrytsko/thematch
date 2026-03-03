"""
Модуль инициализации обработчиков команд бота.
Регистрирует все обработчики и их зависимости.
"""

from .start import register_start_handlers
from .compatibility import register_compatibility_handlers
from .feedback import register_feedback_handlers

__all__ = [
    'register_start_handlers',
    'register_compatibility_handlers',
    'register_feedback_handlers',
    'register_all_handlers'
]

def register_all_handlers(bot, db, zodiac_service, biorhythm_calc, numerology_calc, descriptions):
    """
    Регистрация всех обработчиков бота
    
    Args:
        bot: Экземпляр бота
        db: Экземпляр базы данных
        zodiac_service: Сервис для работы со знаками зодиака
        biorhythm_calc: Калькулятор биоритмов
        numerology_calc: Сервис нумерологии
        descriptions: Сервис описаний
    """
    # Регистрируем базовые команды
    register_start_handlers(bot, db)
    
    # Регистрируем обработчики совместимости
    register_compatibility_handlers(
        bot=bot,
        db=db,
        zodiac_service=zodiac_service,
        biorhythm_calc=biorhythm_calc,
        numerology_calc=numerology_calc,
        descriptions=descriptions
    )
    
    # Регистрируем обработчики обратной связи
    register_feedback_handlers(bot, db)