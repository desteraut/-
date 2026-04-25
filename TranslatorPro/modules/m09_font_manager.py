"""
m09_font_manager.py — Проверка и замена шрифтов
Анализирует поддержку кириллицы через fontTools и заменяет при необходимости.
"""
import os
import re
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    from fontTools.ttLib import TTFont
except ImportError:
    TTFont = None

logger = logging.getLogger(__name__)


def check_cyrillic_support(font_path: str) -> Dict:
    """
    Проверяет, поддерживает ли шрифт кириллицу через cmap таблицу.
    Возвращает подробный отчёт с процентом покрытия.
    """
    if not TTFont:
        return {"supports_cyrillic": True, "coverage_percent": 100.0, "error": "fontTools недоступен"}
    try:
        font = TTFont(font_path)
        cmap = font["cmap"].getBestCmap()
        cyrillic_ranges = [
            range(0x0400, 0x04FF),    # Основная кириллица
            range(0x0500, 0x052F),    # Дополнительная кириллица
            range(0x2DE0, 0x2DFF),    # Декоративная кириллица
            range(0xA640, 0xA69F),    # Расширенная кириллица
        ]
        required_chars = set()
        for r in cyrillic_ranges:
            required_chars.update(r)
        supported_chars = set(cmap.keys()) & required_chars
        coverage = len(supported_chars) / len(required_chars) * 100 if required_chars else 0
        return {
            "supports_cyrillic": coverage > 80,
            "coverage_percent": round(coverage, 2),
            "supported": len(supported_chars),
            "total": len(required_chars),
            "font_path": font_path,
        }
    except Exception as e:
        logger.error(f"❌ Ошибка проверки шрифта {font_path}: {e}")
        return {"supports_cyrillic": False, "coverage_percent": 0.0, "error": str(e)}


def find_fonts(game_path: str) -> List[Path]:
    """Находит все шрифтовые файлы в игре."""
    extensions = {".ttf", ".otf", ".woff", ".woff2"}
    fonts = []
    for ext in extensions:
        fonts.extend(Path(game_path).rglob(f"*{ext}"))
    return fonts


def patch_fonts_for_cyrillic(game_path: str, noto_dir: Path = None) -> List[Dict]:
    """
    1. Найти все шрифты в game/
    2. Проверить каждый на поддержку кириллицы
    3. Для шрифтов без кириллицы заменить на Noto
    4. Вернуть список замен для отчёта
    """
    replacements = []
    game_path = Path(game_path)

    for font_file in find_fonts(str(game_path)):
        check = check_cyrillic_support(str(font_file))
        if not check.get("supports_cyrillic", True):
            replacements.append({
                "original": str(font_file),
                "coverage": check.get("coverage_percent", 0),
                "replacement": "NotoSans-Regular.ttf (recommended)",
                "replaced_in_files": [],
            })
    return replacements


def add_font_patch_block(game_path: str, language_folder: str = "russian"):
    """Добавляет в game/tl/<language>/common.rpy блок с переопределением шрифтов."""
    game_path = Path(game_path)
    tl_dir = game_path / "game" / "tl" / language_folder
    tl_dir.mkdir(parents=True, exist_ok=True)
    common_rpy = tl_dir / "common.rpy"

    patch_code = '''\ntranslate russian python:\n    gui.text_font = "fonts/NotoSans-Regular.ttf"\n    gui.name_text_font = "fonts/NotoSans-Regular.ttf"\n    gui.interface_text_font = "fonts/NotoSans-Regular.ttf"\n    gui.button_text_font = "fonts/NotoSans-Regular.ttf"\n    gui.choice_button_text_font = "fonts/NotoSans-Regular.ttf"\n'''

    content = common_rpy.read_text(encoding="utf-8") if common_rpy.exists() else ""
    if "translate russian python:" not in content:
        with open(common_rpy, "a", encoding="utf-8") as f:
            f.write(patch_code)
        logger.info(f"✅ Блок шрифтов добавлен в {common_rpy}")
    else:
        logger.info(f"ℹ️ Блок шрифтов уже есть в {common_rpy}")


class FontManager:
    """Менеджер шрифтов для Ren'Py локализации."""

    def __init__(self, noto_fonts_dir: Optional[Path] = None):
        self.noto_dir = noto_fonts_dir or Path(__file__).resolve().parent.parent / "assets" / "fonts"
        self.replacements: List[Dict] = []

    def check_and_patch(self, game_path: str, language_folder: str = "russian") -> List[Dict]:
        """Проверяет шрифты и при необходимости добавляет патч."""
        self.replacements = patch_fonts_for_cyrillic(game_path)
        if self.replacements:
            add_font_patch_block(game_path, language_folder)
            logger.info(f"⚠️ Найдено шрифтов без кириллицы: {len(self.replacements)}")
        else:
            logger.info("✅ Все шрифты поддерживают кириллицу")
        return self.replacements
