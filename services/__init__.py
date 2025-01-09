# services/__init__.py

from .zodiac import ZodiacService
from .biorhythm import BiorhythmCalculator
from .numerology import NumerologyCalculator

__all__ = [
    'ZodiacService',
    'BiorhythmCalculator',
    'NumerologyCalculator'
]