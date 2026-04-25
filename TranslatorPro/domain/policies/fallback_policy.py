"""
FallbackPolicy — правила выбора движков перевода
"""

from typing import List, Optional
from ports.engine import TranslationEngine


class FallbackPolicy:
    """Политика выбора движка перевода с fallback"""
    
    def __init__(self, engines: List[TranslationEngine]):
        self.engines = engines
        self.primary_engine: Optional[TranslationEngine] = None
        self.fallback_engine: Optional[TranslationEngine] = None
        
        self._select_engines()
    
    def _select_engines(self):
        """Выбирает основной и резервный движки"""
        available = [e for e in self.engines if e.is_available()]
        
        if len(available) >= 2:
            self.primary_engine = available[0]
            self.fallback_engine = available[1]
        elif len(available) == 1:
            self.primary_engine = available[0]
            self.fallback_engine = None
        else:
            self.primary_engine = None
            self.fallback_engine = None
    
    def get_engine(self) -> Optional[TranslationEngine]:
        """Возвращает доступный движок"""
        if self.primary_engine and self.primary_engine.is_available():
            return self.primary_engine
        if self.fallback_engine and self.fallback_engine.is_available():
            return self.fallback_engine
        return None
    
    def get_available_engines(self) -> List[str]:
        """Возвращает список доступных движков"""
        return [e.get_name() for e in self.engines if e.is_available()]