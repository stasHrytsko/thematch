from .start import register_start_handlers
from .compatibility import register_compatibility_handlers

from .start import register_start_handlers
from .compatibility import register_compatibility_handlers

def register_all_handlers(bot, db, zodiac_service, biorhythm_calc, numerology_calc):
    """Регистрация всех обработчиков"""
    # Регистрируем базовые команды
    register_start_handlers(bot, db)
    
    # Регистрируем обработчики совместимости
    register_compatibility_handlers(
        bot,
        zodiac_service,
        biorhythm_calc,
        numerology_calc
    )