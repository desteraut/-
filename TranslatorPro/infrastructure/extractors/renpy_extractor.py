"""
RenPyExtractor — универсальный экстрактор текста из файлов Ren'Py
Поддержка: .rpy файлы и RPA архивы (.rpyc/.rpymc УДАЛЕНЫ)
Версия: 10.0 — без .rpyc, с централизованными утилитами
"""
import os
import re
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set

logger = logging.getLogger(__name__)

from infrastructure.guards.code_guard import CodeGuard
from infrastructure.utils.rpa_extractor import extract_rpa_with_unrpa
from infrastructure.utils.text_utils import (
    is_file_path, is_rpy_file, generate_text_hash, extract_dialogue
)


class RenPyExtractor:
    """Экстрактор текста из .rpy файлов Ren'Py (без .rpyc)"""

    TEXT_EXTENSIONS = {'.rpy'}
    RPA_EXTENSIONS = {'.rpa'}

    def __init__(self, game_path: str, temp_dir: Optional[str] = None):
        self.game_path = Path(game_path)
        self.game_folder = self.game_path / "game"

        # Если game/ не существует — используем корень
        if not self.game_folder.exists():
            self.game_folder = self.game_path

        # Папка для распаковки RPA — ВНУТРИ game/
        self.temp_dir = self.game_folder
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.code_guard = CodeGuard()
        self.extracted_texts: List[Dict] = []
        self._seen_hashes: Set[str] = set()

        # RPA архивы НЕ распаковываются автоматически — только по кнопке в GUI

    def _extract_rpa_archives(self):
        """Распаковывает все RPA архивы в игре."""
        rpa_files = list(self.game_folder.glob("*.rpa"))

        if not rpa_files:
            logger.info("RPA архивы не найдены")
            return

        logger.info(f"Найдено RPA архивов: {len(rpa_files)}")

        for rpa_file in rpa_files:
            logger.info(f"Распаковка: {rpa_file.name}")
            try:
                success, extracted, errors = extract_rpa_with_unrpa(
                    str(rpa_file),
                    str(self.game_folder)
                )
                if success:
                    logger.info(f"Распакован: {rpa_file.name} -> {self.game_folder}")
                else:
                    logger.warning(f"Не удалось распаковать: {rpa_file.name} (ошибок: {errors})")
            except Exception as e:
                logger.error(f"Ошибка при распаковке {rpa_file.name}: {e}")

        logger.info(f"Все RPA архивы распакованы в: {self.game_folder}")

    def _read_rpy_file(self, rpy_path: Path) -> Optional[str]:
        """Читает .rpy файл напрямую"""
        try:
            return rpy_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Ошибка чтения: {rpy_path} — {e}")
            return None

    def extract_from_file(self, file_path: Path) -> List[Dict]:
        """Извлекает текст из одного .rpy файла"""
        if not is_rpy_file(file_path):
            return []

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            filename = str(file_path.relative_to(self.game_folder)) if file_path.is_relative_to(self.game_folder) else file_path.name
            return extract_dialogue(content, filename, self._seen_hashes, self.code_guard)
        except Exception as e:
            logger.error(f"Ошибка чтения {file_path}: {e}")
            return []

    def extract_all(self) -> List[Dict]:
        """Извлекает текст из всех .rpy файлов игры"""
        logger.info("Начало извлечения текста...")
        self.extracted_texts = []
        self._seen_hashes = set()

        scan_folders = [self.game_folder]
        if self.temp_dir.exists() and self.temp_dir != self.game_folder:
            scan_folders.append(self.temp_dir)

        for folder in scan_folders:
            if not folder.exists():
                continue

            for rpy_file in folder.rglob("*.rpy"):
                if 'tl' in rpy_file.parts or '_extracted' in str(rpy_file):
                    continue
                self.extracted_texts.extend(self.extract_from_file(rpy_file))

        logger.info(f"\nВсего извлечено: {len(self.extracted_texts)} строк")
        return self.extracted_texts

    def cleanup(self):
        """Очищает временные файлы после извлечения"""
        if self.temp_dir.exists() and self.temp_dir != self.game_folder:
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Временные файлы удалены: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Не удалось удалить временные файлы: {e}")
