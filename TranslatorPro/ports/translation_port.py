"""
ports/translation_port.py
Интерфейс для движков перевода (Translation Port)
Clean Architecture - Ports Layer

⚠️  АЛИАС: Это файл-алиас для совместимости с ports/engine.py
Основной интерфейс: TranslationEngine
"""
from .engine import TranslationEngine

# ✅ Экспортируем TranslationEngine как TranslationPort для совместимости
TranslationPort = TranslationEngine

__all__ = ['TranslationPort', 'TranslationEngine']