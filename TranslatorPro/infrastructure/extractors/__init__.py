"""
Extractors — модули извлечения текста.

Доступные:
- RenPyExtractor: Извлечение из .rpy файлов (без .rpyc)
"""
from .renpy_extractor import RenPyExtractor

__all__ = ['RenPyExtractor']
