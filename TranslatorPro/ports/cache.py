"""
CacheInterface — интерфейс для кэша
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class CacheInterface(ABC):
    """Базовый интерфейс для кэша"""
    
    @abstractmethod
    def get_translation(self, original: str, src_lang: str, tgt_lang: str,
                        file_path: str, line_number: int) -> Optional[Dict[str, Any]]:
        """Получение перевода из кэша"""
        pass

    @abstractmethod
    def save_translation(self, original: str, translated: str, src_lang: str,
                         tgt_lang: str, file_path: str, line_number: int,
                         placeholders: Optional[Dict[str, str]] = None) -> None:
        """Сохранение перевода в кэш"""
        pass

    @abstractmethod
    def clear_cache(self, older_than_days: Optional[int] = None) -> None:
        """Очистка кэша"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        pass