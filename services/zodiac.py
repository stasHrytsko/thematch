from datetime import datetime
from typing import Dict, Tuple, Optional

from datetime import datetime

class ZodiacService:
    """Сервис для расчета зодиакальной совместимости"""
    
    ELEMENTS_ICONS = {
        'Огонь': '🔥',
        'Земля': '🌍',
        'Воздух': '💨',
        'Вода': '💧'
    }

    ZODIAC_RANGES = [
        ('♈', 'Овен', (3, 21), (4, 19)),
        ('♉', 'Телец', (4, 20), (5, 20)),
        ('♊', 'Близнецы', (5, 21), (6, 20)),
        ('♋', 'Рак', (6, 21), (7, 22)),
        ('♌', 'Лев', (7, 23), (8, 22)),
        ('♍', 'Дева', (8, 23), (9, 22)),
        ('♎', 'Весы', (9, 23), (10, 22)),
        ('♏', 'Скорпион', (10, 23), (11, 21)),
        ('♐', 'Стрелец', (11, 22), (12, 21)),
        ('♑', 'Козерог', (12, 22), (1, 19)),
        ('♒', 'Водолей', (1, 20), (2, 18)),
        ('♓', 'Рыбы', (2, 19), (3, 20))
    ]

    ELEMENTS = {
        'Огонь': ['♈', '♌', '♐'],
        'Земля': ['♉', '♍', '♑'],
        'Воздух': ['♊', '♎', '♒'],
        'Вода': ['♋', '♏', '♓']
    }

    # Вот матрица совместимости
    COMPATIBILITY_MATRIX = [
        [70, 65, 85, 45, 90, 55, 80, 50, 90, 40, 85, 50],  # Овен
        [65, 75, 60, 85, 65, 90, 75, 90, 55, 85, 60, 85],  # Телец
        [85, 60, 70, 60, 85, 75, 90, 65, 85, 55, 90, 60],  # Близнецы
        [45, 85, 60, 75, 50, 80, 60, 90, 45, 85, 50, 95],  # Рак
        [90, 65, 85, 50, 70, 60, 85, 55, 90, 45, 85, 50],  # Лев
        [55, 90, 75, 80, 60, 75, 70, 85, 60, 90, 65, 85],  # Дева
        [80, 75, 90, 60, 85, 70, 70, 75, 85, 65, 90, 65],  # Весы
        [50, 90, 65, 90, 55, 85, 75, 75, 55, 85, 60, 90],  # Скорпион
        [90, 55, 85, 45, 90, 60, 85, 55, 70, 55, 85, 50],  # Стрелец
        [40, 85, 55, 85, 45, 90, 65, 85, 55, 75, 65, 85],  # Козерог
        [85, 60, 90, 50, 85, 65, 90, 60, 85, 65, 70, 55],  # Водолей
        [50, 85, 60, 95, 50, 85, 65, 90, 50, 85, 55, 75]   # Рыбы
    ]

    def calculate_zodiac_compatibility(self, date1: datetime, date2: datetime) -> Tuple[float, Dict]:
        """
        Рассчитывает общую совместимость по гороскопу
        Returns: (общий процент, детали расчета)
        """
        sign1 = self.get_zodiac_sign(date1)
        sign2 = self.get_zodiac_sign(date2)
        
        element1 = self.get_element(sign1)
        element2 = self.get_element(sign2)
        
        signs_comp = self.get_signs_compatibility(sign1, sign2)
        elements_comp = self.get_elements_compatibility(element1, element2)
        
        # Финальный расчет зодиакальной совместимости
        total_compatibility = round((signs_comp * 0.75) + (elements_comp * 0.25), 1)
        
        details = {
            'sign1': sign1,
            'sign2': sign2,
            'element1': element1,
            'element2': element2,
            'signs_compatibility': round(signs_comp, 1),
            'elements_compatibility': round(elements_comp, 1)
        }
        
        return total_compatibility, details

    def get_element(self, sign: str) -> Optional[str]:
        """Определяет стихию знака"""
        for element, signs in self.ELEMENTS.items():
            if sign in signs:
                return element
        return None

    def get_elements_compatibility(self, element1: str, element2: str) -> float:
        """Рассчитывает совместимость стихий"""
        if element1 == element2:
            return 70  # Одинаковые стихии
        elif (element1 == 'Огонь' and element2 == 'Воздух') or \
             (element1 == 'Воздух' and element2 == 'Огонь'):
            return 90  # Огонь-Воздух
        elif (element1 == 'Земля' and element2 == 'Вода') or \
             (element1 == 'Вода' and element2 == 'Земля'):
            return 90  # Земля-Вода
        return 50  # Другие комбинации

    def get_zodiac_sign(self, date: datetime) -> Optional[str]:
        """Определяет знак зодиака по дате"""
        month = date.month
        day = date.day
        
        for symbol, _, start, end in self.ZODIAC_RANGES:
            if (month == start[0] and day >= start[1]) or \
               (month == end[0] and day <= end[1]):
                return symbol
        
        # Для Козерога (переход через год)
        if month == 12 and day >= 22 or month == 1 and day <= 19:
            return self.ZODIAC_RANGES[9][0]  # Козерог
        
        return None

    def get_signs_compatibility(self, sign1: str, sign2: str) -> float:
        """Возвращает процент совместимости между двумя знаками"""
        sign1_index = next(i for i, (symbol, _, _, _) in enumerate(self.ZODIAC_RANGES) if symbol == sign1)
        sign2_index = next(i for i, (symbol, _, _, _) in enumerate(self.ZODIAC_RANGES) if symbol == sign2)
        return self.COMPATIBILITY_MATRIX[sign1_index][sign2_index]

    def get_sign_name(self, sign: str) -> str:
        """Returns zodiac sign name for symbol"""
        sign_names = {
            '♈': 'Овен',
            '♉': 'Телец',
            '♊': 'Близнецы',
            '♋': 'Рак',
            '♌': 'Лев',
            '♍': 'Дева',
            '♎': 'Весы',
            '♏': 'Скорпион',
            '♐': 'Стрелец',
            '♑': 'Козерог',
            '♒': 'Водолей',
            '♓': 'Рыбы'
        }
        return sign_names.get(sign, "Неизвестный знак")