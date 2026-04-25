"""
TextExtractor — интерфейс для экстракторов текста
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict


class TextExtractor(ABC):
    """Базовый класс для экстракторов текста"""
    
    @abstractmethod
    def extract_from_file(self, file_path: Path) -> List[Dict]:
        """Извлекает текст из файла"""
        pass
    
    @abstractmethod
    def extract_all(self) -> List[Dict]:
        """Извлекает текст из всех файлов"""
        pass