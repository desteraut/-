"""
Engines — движки перевода.
"""
from .base_engine import BaseTranslationEngine
from .argos_engine import ArgosEngine
from .nllb_engine import NLLBEngine
from .engine_manager import EngineManager

__all__ = [
    'BaseTranslationEngine',
    'ArgosEngine',
    'NLLBEngine',
    'EngineManager',
]
