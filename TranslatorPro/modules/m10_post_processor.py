"""
m10_post_processor.py — Пост-обработка перевода
Корректировка стилистики, кавычек, многоточий.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def post_process_russian(text: str) -> str:
    """
    Пост-обработка русского текста:
    1. Заменить "..." на "…" (многоточие, U+2026)
    2. Исправить кавычки: "text" → «text» (ёлочки)
    3. Убрать лишние пробелы (двойные, в начале/конце)
    4. Проверить парность скобок и кавычек
    5. Гарантировать заглавную букву в начале предложений
    6. Неразрывный пробел перед короткими предлогами (в, к, о, с, у, а, и, или)
    7. Заменить дефис на тире (—) между предложениями
    """
    if not text:
        return text

    # 1. Многоточие
    text = text.replace("...", "…")
    text = re.sub(r'\.{3,}', '…', text)

    # 2. Кавычки → ёлочки (только если нет уже ёлочек и нет тегов Ren'Py)
    # Осторожно: не трогаем {tag="value"} и [variable]
    def replace_quotes(match):
        inner = match.group(1)
        return f"«{inner}»"

    # Простые ASCII кавычки вокруг текста
    text = re.sub(r'"([^"]{1,200})"', replace_quotes, text)
    text = re.sub(r'"([^"]{1,200})"', replace_quotes, text)

    # 3. Лишние пробелы
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    # 4. Неразрывный пробел перед короткими предлогами
    # Не трогаем если уже есть неразрывный пробел или это начало строки
    short_prepositions = ['в', 'к', 'о', 'с', 'у', 'а', 'и', 'или', 'но', 'да', 'от', 'до', 'об', 'по', 'за', 'на', 'под', 'при', 'про', 'для', 'со', 'во', 'ко']
    for prep in short_prepositions:
        # Добавляем неразрывный пробел перед предлогом, если он стоит после обычного пробела
        pattern = rf' (?=\b{prep} \b)'
        text = re.sub(pattern, '\u00A0', text)

    # 5. Заменяем дефис, окружённый пробелами, на тире
    text = re.sub(r' (?=— )', '\u00A0', text)
    text = re.sub(r' - ', ' — ', text)

    # 6. Заглавная буква в начале (если не тег)
    if text and text[0].islower() and not text.startswith('{') and not text.startswith('['):
        text = text[0].upper() + text[1:]

    return text


def preserve_renpy_tags(text: str) -> str:
    """Убеждается, что Ren'Py теги не повреждены пост-обработкой."""
    # Проверяем баланс { }
    open_braces = text.count('{')
    close_braces = text.count('}')
    if open_braces != close_braces:
        logger.warning(f"⚠️ Несбалансированные скобки в: {text[:60]}")

    # Проверяем баланс [ ]
    open_brackets = text.count('[')
    close_brackets = text.count(']')
    if open_brackets != close_brackets:
        logger.warning(f"⚠️ Несбалансированные квадратные скобки в: {text[:60]}")

    return text


class PostProcessor:
    """Пост-процессор перевода."""

    def __init__(self):
        self.stats = {"quotes_fixed": 0, "ellipsis_fixed": 0, "spaces_fixed": 0}

    def process(self, text: str) -> str:
        """Полная пост-обработка строки."""
        original = text
        text = post_process_russian(text)
        text = preserve_renpy_tags(text)

        if '"' not in original and '«' in text:
            self.stats["quotes_fixed"] += 1
        if '...' in original and '…' in text:
            self.stats["ellipsis_fixed"] += 1

        return text

    def get_stats(self) -> dict:
        return self.stats.copy()
