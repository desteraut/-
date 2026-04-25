"""
m08_text_fitter.py — Адаптация длины текста
Проверяет ширину переведённого текста и добавляет мягкие переносы.
"""
import re
import logging
from pathlib import Path
from typing import Tuple, Optional

try:
    from PIL import ImageFont
except ImportError:
    ImageFont = None

try:
    import pyphen
except ImportError:
    pyphen = None

logger = logging.getLogger(__name__)


class TextFitter:
    """Адаптирует переведённый текст под заданную ширину."""

    def __init__(self, font_path: Optional[Path] = None, font_size: int = 22, max_width: int = 600):
        self.font_path = str(font_path) if font_path else None
        self.font_size = font_size
        self.max_width = max_width
        self.hyphenator = pyphen.Pyphen(lang='ru_RU') if pyphen else None

    def measure_text_width(self, text: str) -> int:
        """Измеряет ширину текста в пикселях."""
        if not ImageFont or not self.font_path:
            # Fallback: примерно 0.6 от размера шрифта на символ
            return int(len(text) * self.font_size * 0.6)
        try:
            font = ImageFont.truetype(self.font_path, self.font_size)
            bbox = font.getbbox(text)
            return bbox[2] - bbox[0]  # right - left
        except Exception:
            return int(len(text) * self.font_size * 0.6)

    def add_soft_hyphens(self, text: str) -> str:
        """Добавляет \u00AD (мягкий перенос) для длинных слов (>6 символов)."""
        if not self.hyphenator:
            return text
        words = text.split()
        processed = []
        for word in words:
            # Очистка слова от тегов Ren'Py для проверки длины
            clean_word = re.sub(r'\{[^}]+\}', '', word)
            clean_word = re.sub(r'\[[^\]]+\]', '', clean_word)
            if len(clean_word) > 6:
                hyphenated = self.hyphenator.inserted(clean_word)
                # Заменяем чистое слово на с переносами, сохраняя теги
                if clean_word != word:
                    processed.append(word)
                else:
                    processed.append(hyphenated)
            else:
                processed.append(word)
        return ' '.join(processed)

    def fit_text(self, text: str) -> Tuple[str, int]:
        """
        Адаптирует текст под max_width:
        1. Проверить текущую ширину
        2. Если превышает — добавить мягкие переносы
        3. Если всё ещё превышает — уменьшить размер шрифта на 10%
        4. Возвращает (adapted_text, adjusted_font_size)
        """
        width = self.measure_text_width(text)
        if width <= self.max_width:
            return text, self.font_size

        # Пробуем с мягкими переносами
        hyphenated = self.add_soft_hyphens(text)
        h_width = self.measure_text_width(hyphenated)
        if h_width <= self.max_width:
            return hyphenated, self.font_size

        # Уменьшаем размер шрифта
        adjusted_size = int(self.font_size * (self.max_width / width) * 0.95)
        return hyphenated, max(adjusted_size, 12)

    def process_translation(self, text: str) -> str:
        """
        Обрабатывает переведённую строку:
        1. Добавляет мягкие переносы если нужно
        2. НЕ добавляет Ren'Py теги {size=-N} — они ломают целостность и совместимость
        """
        # Не обрабатываем очень короткие тексты
        if len(text) < 10:
            return text
        fitted_text, _ = self.fit_text(text)
        return fitted_text
