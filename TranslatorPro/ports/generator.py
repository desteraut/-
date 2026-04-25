"""
FileGenerator — интерфейс для генераторов файлов
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict


class FileGenerator(ABC):
    """Базовый класс для генераторов файлов"""
    
    @abstractmethod
    def generate(self, translations: List[Dict], output_dir: Path) -> Path:
        """Генерирует файлы перевода"""
        pass