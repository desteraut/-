"""
Helpers — вспомогательные функции для TranslatorPro V3
ИСПРАВЛЕНО: __name__, поддержка §§VAR_...§§
Согласно PDF "Решение ключевых проблем локализации в Ren'Py"
"""
import re
import hashlib
from pathlib import Path
from typing import Dict, Tuple, Optional
import logging

# ✅ ИСПРАВЛЕНО: __name__ вместо name
logger = logging.getLogger(__name__)


def escape_renpy_string(text: str) -> str:
    """Экранирует строку для Ren'Py"""
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    return text


def protect_placeholders(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Защищает плейсхолдеры перед переводом
    ✅ ИСПРАВЛЕНО: Добавлена поддержка §§VAR_...§§
    """
    protected = {}
    counter = [0]
    
    def replace_placeholder(match):
        placeholder = f"###PH{counter[0]}###"
        protected[placeholder] = match.group(0)
        counter[0] += 1
        return placeholder

    # ✅ Сначала защищаем §§VAR_...§§ (Ren'Py compiled format)
    text = re.sub(r'§§VAR_[^§]+§§', replace_placeholder, text)
    # Затем стандартные [variable] и {variable}
    text = re.sub(r'(\[.*?\]|\{.*?\})', replace_placeholder, text)

    logger.debug(f"Protected {len(protected)} placeholders")
    return text, protected


def restore_placeholders(text: str, protected: Dict[str, str]) -> str:
    """Восстанавливает плейсхолдеры после перевода"""
    for placeholder, original in protected.items():
        text = text.replace(placeholder, original)
    logger.debug(f"Restored {len(protected)} placeholders")
    return text


def generate_hash(text: str) -> str:
    """Генерирует MD5 хеш текста"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def is_safe_path(base_path: Path, target_path: Path) -> bool:
    """Проверяет, что target_path находится внутри base_path"""
    try:
        base_path = base_path.resolve()
        target_path = target_path.resolve()
        target_path.relative_to(base_path)
        return True
    except ValueError:
        logger.warning(f"Unsafe path detected: {target_path} is not within {base_path}")
        return False


def ensure_dir(path: Path) -> Path:
    """Создаёт директорию, если она не существует"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_encoding(filepath: Path) -> str:
    """Определяет кодировку файла"""
    return 'utf-8'


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезает текст до максимальной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."