from datetime import datetime
from typing import Tuple, Dict

class NumerologyCalculator:
    """Сервис для нумерологических расчетов и определения совместимости"""
    
    # Матрица совместимости чисел судьбы (значения в процентах)
    COMPATIBILITY_MATRIX = [
        # 1   2   3   4   5   6   7   8   9
        [95, 60, 90, 50, 85, 70, 65, 90, 75],  # 1
        [60, 90, 65, 90, 55, 95, 50, 60, 80],  # 2
        [85, 65, 75, 60, 95, 70, 85, 75, 90],  # 3
        [55, 80, 60, 70, 65, 85, 55, 95, 65],  # 4
        [75, 55, 95, 65, 80, 60, 90, 70, 85],  # 5
        [65, 75, 70, 85, 60, 85, 65, 75, 90],  # 6
        [80, 60, 85, 55, 90, 65, 75, 60, 95],  # 7
        [50, 75, 65, 85, 50, 80, 60, 90, 65],  # 8
        [70, 50, 85, 60, 80, 55, 75, 65, 90]   # 9
    ]

    @staticmethod
    def calculate_life_path_number(birth_date: datetime) -> int:
        """
        Вычисляет число судьбы по дате рождения
        
        Args:
            birth_date: Дата рождения
            
        Returns:
            int: Число судьбы (1-9)
        """
        # Преобразуем дату в строку формата ДДММГГГГ
        date_str = birth_date.strftime('%d%m%Y')
        
        # Суммируем все цифры
        while len(date_str) > 1:
            total = sum(int(digit) for digit in date_str)
            date_str = str(total)
            
        # Проверяем чтобы число было от 1 до 9
        result = int(date_str)
        if result > 9:
            result = sum(int(digit) for digit in str(result))
        
        return result

    def calculate_compatibility(self, date1: datetime, date2: datetime) -> Tuple[float, Dict]:
        """
        Вычисляет нумерологическую совместимость двух дат
        
        Args:
            date1: Дата рождения первого человека
            date2: Дата рождения второго человека
            
        Returns:
            Tuple[float, Dict]: (процент совместимости, детали расчета)
        """
        # Получаем числа судьбы
        number1 = self.calculate_life_path_number(date1)
        number2 = self.calculate_life_path_number(date2)
        
        # Получаем процент совместимости из матрицы
        compatibility = self.COMPATIBILITY_MATRIX[number1 - 1][number2 - 1]
        
        # Формируем детали для вывода
        details = {
            'number1': number1,
            'number2': number2,
            'compatibility': compatibility,
            'description1': self.get_number_description(number1),
            'description2': self.get_number_description(number2)
        }
        
        return compatibility, details

    @staticmethod
    def get_number_description(number: int) -> str:
        """
        Возвращает описание числа судьбы
        
        Args:
            number: Число судьбы (1-9)
            
        Returns:
            str: Описание числа
        """
        descriptions = {
            1: "Лидер, инициатор, независимая личность",
            2: "Дипломат, миротворец, чуткая душа",
            3: "Творец, коммуникатор, яркая личность",
            4: "Строитель, организатор, надежный человек",
            5: "Искатель свободы, динамичная натура",
            6: "Наставник, хранитель, заботливая личность",
            7: "Мыслитель, философ, глубокая личность",
            8: "Руководитель, стратег, амбициозная натура",
            9: "Гуманист, идеалист, мудрая душа"
        }
        return descriptions.get(number, "Неизвестное число")