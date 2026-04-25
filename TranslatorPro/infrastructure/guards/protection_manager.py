"""
ProtectionManager — защита плейсхолдеров [var], {tag}
ИСПРАВЛЕНО: возвращает СТРОКУ, а не кортеж!
Совместим со старым LocalizationPipeline
"""
import re
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ProtectionManager:
    """Защищает переменные и теги от перевода"""
    
    def __init__(self):
        self.placeholders: Dict[str, str] = {}
        self._counter = 0
    
    def protect(self, text: str) -> str:
        """
        Заменяет плейсхолдеры на маркеры
        ✅ ВАЖНО: Возвращает СТРОКУ, не кортеж!
        Плейсхолдеры сохраняются в self.placeholders
        ✅ ИСПРАВЛЕНО: Не захватывает [NTP:...] маркеры CodeProtector
        """
        self.placeholders = {}
        self._counter = 0
        
        # Паттерн 1: [variable] — ИСКЛЮЧАЕМ [NTP:...] маркеры
        def replace_brackets(match):
            original = match.group(0)
            # Не трогаем NTP маркеры CodeProtector
            if original.startswith('[NTP') or original.startswith('[ntp'):
                return original
            self._counter += 1
            marker = f"###PH_{self._counter}###"
            self.placeholders[marker] = original
            return marker
        
        text = re.sub(r'\[[a-zA-Z_][a-zA-Z0-9_]*\]', replace_brackets, text)
        
        # Паттерн 2: {variable}
        def replace_braces(match):
            self._counter += 1
            original = match.group(0)
            marker = f"###PH_{self._counter}###"
            self.placeholders[marker] = original
            return marker
        
        text = re.sub(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', replace_braces, text)
        
        return text  # ✅ Возвращаем СТРОКУ
    
    def restore(self, text: str) -> str:
        """
        Восстанавливает плейсхолдеры
        ✅ ВАЖНО: Возвращает СТРОКУ, не кортеж!
        """
        for marker, original in self.placeholders.items():
            text = text.replace(marker, original)
        return text  # ✅ Возвращаем СТРОКУ
    
    def protect_all(self, text: str) -> str:
        """Алиас для protect() для совместимости"""
        return self.protect(text)
    
    def restore_all(self, text: str) -> str:
        """Алиас для restore() для совместимости"""
        return self.restore(text)
    
    def get_placeholders_count(self) -> int:
        """Возвращает количество защищённых плейсхолдеров"""
        return len(self.placeholders)