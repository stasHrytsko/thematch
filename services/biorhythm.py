from datetime import datetime
from typing import Dict, Tuple
import math

class BiorhythmCalculator:
    """Сервис для расчета совместимости биоритмов"""
    
    # Периоды биоритмов в сутках
    CYCLES = {
        'physical': 23.6884,      # Муладхара
        'emotional': 28.426125,   # Свадхистана
        'intellectual': 33.163812, # Манипура
        'heart': 37.901499,      # Анахата
        'creative': 42.6392,      # Вишудха
        'intuitive': 47.3769,     # Аджна
        'higher': 52.1146        # Сахасрара
    }
    
    # Веса чакр (в сумме 100%)
    CHAKRA_WEIGHTS = {
        'higher': 0.20,      # Сахасрара (20%)
        'intuitive': 0.20,   # Аджна (20%)
        'creative': 0.15,    # Вишудха (15%)
        'heart': 0.15,       # Анахата (15%)
        'intellectual': 0.10, # Манипура (10%)
        'emotional': 0.10,   # Свадхистана (10%)
        'physical': 0.10     # Муладхара (10%)
    }

    def calculate_days(self, birth_date: datetime) -> float:
        """Вычисляет количество дней с даты рождения"""
        current_date = datetime.now()
        return (current_date - birth_date).total_seconds() / (24 * 3600)

    def calculate_phase(self, days: float, cycle_length: float) -> float:
        """Вычисляет фазу биоритма"""
        return (days / cycle_length) * 2 * math.pi

    def calculate_biorhythm_value(self, phase: float) -> float:
        """
        Вычисляет значение биоритма в процентах
        
        Args:
            phase: Фаза биоритма
            
        Returns:
            float: Значение от 0 до 100
        """
        sin_value = math.sin(phase)
        percentage = ((sin_value + 1) / 2) * 100
        return max(0, min(100, percentage))

    def calculate_phase_compatibility(self, phase1: float, phase2: float) -> float:
        """
        Вычисляет совместимость фаз биоритмов
        
        Args:
            phase1: Фаза первого биоритма
            phase2: Фаза второго биоритма
            
        Returns:
            float: Процент совместимости (0-100)
        """
        # Нормализуем фазы к интервалу [0, 2π]
        phase1 = phase1 % (2 * math.pi)
        phase2 = phase2 % (2 * math.pi)
        
        # Вычисляем разницу фаз
        phase_diff = abs(phase1 - phase2)
        
        # Берем меньшую разницу через окружность
        if phase_diff > math.pi:
            phase_diff = 2 * math.pi - phase_diff
            
        # Рассчитываем совместимость
        compatibility = (1.0 - phase_diff / math.pi) * 100
        
        return max(0, min(100, compatibility))

    def calculate_personal_biorhythms(self, birth_date: datetime) -> Dict[str, Dict[str, float]]:
        """
        Вычисляет все биоритмы для одного человека
        
        Args:
            birth_date: Дата рождения
            
        Returns:
            Dict с результатами для каждого биоритма
        """
        days = self.calculate_days(birth_date)
        results = {}
        
        for rhythm_name, cycle_length in self.CYCLES.items():
            phase = self.calculate_phase(days, cycle_length)
            value = self.calculate_biorhythm_value(phase)
            results[rhythm_name] = {
                'phase': phase,
                'value': value
            }
        
        return results

    def calculate_compatibility(self, date1: datetime, date2: datetime) -> Tuple[float, Dict]:
        """
        Вычисляет совместимость биоритмов двух людей
        
        Args:
            date1: Дата рождения первого человека
            date2: Дата рождения второго человека
            
        Returns:
            Tuple[float, Dict]: (общая совместимость, детальные результаты)
        """
        bio1 = self.calculate_personal_biorhythms(date1)
        bio2 = self.calculate_personal_biorhythms(date2)
        
        compatibilities = {}
        total_compatibility = 0
        
        # Вычисляем совместимость для каждого биоритма
        for rhythm_name in self.CYCLES.keys():
            phase_comp = self.calculate_phase_compatibility(
                bio1[rhythm_name]['phase'],
                bio2[rhythm_name]['phase']
            )
            
            # Ограничиваем значения от 0 до 100
            value1 = min(100, max(0, bio1[rhythm_name]['value']))
            value2 = min(100, max(0, bio2[rhythm_name]['value']))
            
            compatibilities[rhythm_name] = {
                'compatibility': phase_comp,
                'value1': value1,
                'value2': value2
            }
            
            # Добавляем к общей совместимости с учетом веса чакры
            total_compatibility += phase_comp * self.CHAKRA_WEIGHTS[rhythm_name]
        
        # Убеждаемся, что итоговая совместимость тоже не превышает 100%
        total_compatibility = round(total_compatibility, 2)
        
        # Формируем детали для вывода
        details = {
            'total': round(total_compatibility, 2),
            'rhythms': {
                name: {
                    'compatibility': round(data['compatibility'], 2),
                    'person1': round(data['value1'], 2),
                    'person2': round(data['value2'], 2)
                }
                for name, data in compatibilities.items()
            }
        }
        
        return total_compatibility, details