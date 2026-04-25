"""
BaseTranslationEngine — базовый интерфейс для всех движков перевода
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseTranslationEngine(ABC):
    """Базовый класс для движков перевода"""
    
    def __init__(self, source_lang: str = "en", target_lang: str = "russian"):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.is_ready = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """Инициализация движка"""
        pass
    
    @abstractmethod
    def translate(self, text: str) -> str:
        """Перевод текста"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Проверка доступности движка"""
        pass
    
    def get_name(self) -> str:
        """Возвращает имя движка"""
        return self.__class__.__name__