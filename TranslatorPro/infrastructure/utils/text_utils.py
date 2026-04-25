"""
Общие утилиты для работы с текстом Ren'Py.
Централизованные функции для экстракторов и генераторов.
"""
import re
from pathlib import Path
from typing import List, Dict, Set, Optional
import hashlib
import logging

logger = logging.getLogger(__name__)

# === ОБЩИЕ КОНСТАНТЫ ===
SKIP_EXTENSIONS = {
    '.webp', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tga',
    '.mp3', '.ogg', '.wav', '.opus',
    '.mp4', '.avi', '.webm',
    '.ttf', '.otf', '.fnt',
    '.py', '.pyc', '.pickle', '.data'
}

PATH_PREFIXES = ['images/', 'audio/', 'music/', 'sounds/', 'fonts/', 'gui/', 'bg/']

TEXT_EXTENSIONS = {'.rpy'}


def is_file_path(text: str) -> bool:
    """Проверяет, является ли строка путём к файлу ресурса."""
    if not text:
        return False
    text_lower = text.lower().strip()
    for ext in SKIP_EXTENSIONS:
        if text_lower.endswith(ext):
            return True
    for prefix in PATH_PREFIXES:
        if text_lower.startswith(prefix):
            return True
    if '/' in text and '.' in text and len(text) > 10:
        return True
    return False


def is_rpy_file(path: Path) -> bool:
    """Проверяет, является ли файл .rpy файлом Ren'Py (не options.rpy, не в tl/)."""
    return (path.suffix in TEXT_EXTENSIONS and
            path.name != 'options.rpy' and
            'tl' not in path.parts)


def generate_text_hash(filename: str, line_num: int, text: str) -> str:
    """Генерирует уникальный хэш для строки текста."""
    return hashlib.md5(f"{filename}:{line_num}:{text}".encode()).hexdigest()


def escape_quotes_renpy(text: str) -> str:
    """Экранирует кавычки и спецсимволы для Ren'Py."""
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\t', '\\t')
    return text


def extract_dialogue(content: str, filename: str,
                     seen_hashes: Optional[Set[str]] = None,
                     code_guard=None) -> List[Dict]:
    """
    Извлекает диалоги, меню и строки интерфейса из содержимого .rpy файла.
    
    Args:
        content: Содержимое файла
        filename: Имя файла
        seen_hashes: Множество уже виденных хэшей (для дедупликации)
        code_guard: Опциональный CodeGuard для фильтрации кода
    
    Returns:
        Список словарей с извлечёнными текстами
    """
    texts = []
    lines = content.splitlines()
    in_menu = False
    menu_indent = 0
    local_seen = seen_hashes or set()

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        # Меню
        if stripped.startswith('menu:'):
            in_menu = True
            menu_indent = len(line) - len(line.lstrip())
            continue

        if in_menu:
            current_indent = len(line) - len(line.lstrip())
            if stripped and current_indent <= menu_indent:
                if re.match(r'^(label|init|define|default|screen|style|image|transform)\s+', stripped):
                    in_menu = False

        # Диалог: speaker "text" или "text"
        # Требуем конец строки (или комментарий) после кавычек, чтобы не захватывать Ren'Py statements
        dialogue_match = re.search(r'^\s*(?:(\w+)\s+)?["]([^"]+)["]\s*(?:#.*)?$', line)
        if not dialogue_match:
            dialogue_match = re.search(r'^\s*(?:(\w+)\s+)?["]{3}(.+?)["]{3}\s*(?:#.*)?$', line, re.DOTALL)
        if not dialogue_match:
            dialogue_match = re.search(r"^\s*(?:(\w+)\s+)?'([^']+)'\s*(?:#.*)?$", line)

        if dialogue_match:
            speaker = dialogue_match.group(1) or ""
            text = dialogue_match.group(2).strip()

            if is_file_path(text) or len(text) < 2:
                continue
            if code_guard and hasattr(code_guard, 'is_code_line') and code_guard.is_code_line(text):
                continue

            text_hash = generate_text_hash(filename, line_num, text)
            if text_hash in local_seen:
                continue
            local_seen.add(text_hash)

            texts.append({
                "file": filename,
                "line": line_num,
                "type": "menu" if in_menu else "dialogue",
                "speaker": speaker,
                "text": text,
                "original": line
            })
            continue

        # Строки интерфейса: _("text")
        localize_match = re.search(r'_\s*\(\s*["]([^"]+)["]\s*\)', line)
        if not localize_match:
            localize_match = re.search(r"_\s*\(\s*'([^']+)'\s*\)", line)
        if localize_match:
            text = localize_match.group(1).strip()
            if is_file_path(text) or len(text) < 2:
                continue
            text_hash = generate_text_hash(filename, line_num, text)
            if text_hash in local_seen:
                continue
            local_seen.add(text_hash)

            texts.append({
                "file": filename,
                "line": line_num,
                "type": "interface",
                "speaker": "",
                "text": text,
                "original": line
            })

    return texts
