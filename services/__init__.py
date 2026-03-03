# services/__init__.py
from .zodiac import ZodiacService
from .biorhythm import BiorhythmCalculator
from .numerology import NumerologyService  

__all__ = [
    'ZodiacService',
    'BiorhythmCalculator',
    'NumerologyService'  
]