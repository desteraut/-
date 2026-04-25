"""
m03_rpa_extractor.py — Распаковка RPA-архивов Ren'Py
Обёртка над unrpa с обработкой ошибок.
ИСПРАВЛЕНО: Dict импорт
"""
import logging
from pathlib import Path
from typing import Tuple, List, Dict

try:
    from infrastructure.utils.rpa_extractor import extract_rpa_with_unrpa
    UNRPA_AVAILABLE = True
except ImportError:
    UNRPA_AVAILABLE = False

logger = logging.getLogger(__name__)


class RPAExtractor:
    """
    Модуль m03: Извлекает ресурсы из .rpa архивов Ren'Py.
    """

    def __init__(self, game_path: str, output_subdir: str = "unpacked"):
        self.game_path = Path(game_path)
        self.game_folder = self.game_path / "game"
        if not self.game_folder.exists():
            self.game_folder = self.game_path
        self.output_dir = self.game_folder / output_subdir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_files: List[str] = []
        self.errors: List[str] = []

    def find_rpa_files(self) -> List[Path]:
        """Находит все .rpa файлы в папке game/"""
        rpa_files = list(self.game_folder.glob("*.rpa"))
        logger.info(f"m03: Найдено RPA архивов: {len(rpa_files)}")
        return rpa_files

    def extract(self, rpa_file: Path, override_output: Path = None) -> Tuple[bool, List[str], List[str]]:
        """
        Распаковывает один RPA архив.

        Returns:
            (success, extracted_files, errors)
        """
        if not UNRPA_AVAILABLE:
            logger.error("m03: unrpa не доступен. Установите: pip install unrpa")
            return False, [], ["unrpa не установлен"]

        output = override_output or self.output_dir
        output.mkdir(parents=True, exist_ok=True)

        logger.info(f"m03: Распаковка {rpa_file.name} -> {output}")

        try:
            success, extracted, errs = extract_rpa_with_unrpa(str(rpa_file), str(output))
            if success:
                self.extracted_files.extend(extracted)
                logger.info(f"m03: Распаковано {len(extracted)} файлов из {rpa_file.name}")
            else:
                self.errors.extend(errs)
                logger.warning(f"m03: Ошибки при распаковке {rpa_file.name}: {errs}")
            return success, extracted, errs
        except Exception as e:
            error_msg = f"{rpa_file.name}: {str(e)}"
            self.errors.append(error_msg)
            logger.error(f"m03: {error_msg}")
            return False, [], [error_msg]

    def extract_all(self) -> Tuple[int, int]:
        """
        Распаковывает все RPA архивы.

        Returns:
            (success_count, total_count)
        """
        rpa_files = self.find_rpa_files()
        if not rpa_files:
            return 0, 0

        success_count = 0
        for rpa_file in rpa_files:
            success, _, _ = self.extract(rpa_file)
            if success:
                success_count += 1

        logger.info(f"m03: Распаковано {success_count}/{len(rpa_files)} архивов")
        return success_count, len(rpa_files)

    def get_stats(self) -> Dict:
        """Возвращает статистику распаковки"""
        return {
            "extracted_files": len(self.extracted_files),
            "errors": len(self.errors),
            "output_dir": str(self.output_dir)
        }
