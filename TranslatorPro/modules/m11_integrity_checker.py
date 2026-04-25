"""
m11_integrity_checker.py — Проверка целостности перевода
"""
import re
import logging
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)


def verify_translation_integrity(original: str, translated: str) -> Tuple[bool, List[str]]:
    """
    Проверяет, что после перевода:
    1. В переведённом тексте НЕТ оставшихся [NTP:...] плейсхолдеров
    2. Количество {тегов} Ren'Py совпадает с оригиналом (только оригинальные RenPy теги)
    3. Все кавычки на месте (непарные — ошибка)
    4. Количество переменных [var] совпадает
    5. Нет оставшихся ###PH_### или ###TERM_### маркеров
    6. RenPy теги сбалансированы (открывающие/закрывающие)

    Возвращает: (is_valid, list_of_errors)
    """
    errors: List[str] = []

    # 1. ❌ Оставшиеся NTP плейсхолдеры в переведённом тексте (КРИТИЧНО)
    remaining_ntp = re.findall(r'\[NTP\]\d+', translated)
    if remaining_ntp:
        errors.append(f"unrestored_ntp: {len(remaining_ntp)} leftover")
    
    # 2. ❌ Оставшиеся ###PH_### маркеры
    remaining_ph = re.findall(r'###PH_\d+###', translated)
    if remaining_ph:
        errors.append(f"unrestored_ph: {len(remaining_ph)} leftover")
    
    # 3. ❌ Оставшиеся ###TERM_### маркеры
    remaining_term = re.findall(r'###TERM_[a-f0-9]{8}###', translated)
    if remaining_term:
        errors.append(f"unrestored_term: {len(remaining_term)} leftover")

    # 4. Ren'Py теги {tag} — проверяем ТОЛЬКО оригинальные RenPy теги (не NTP!)
    # Фильтруем NTP плейсхолдеры из оригинала перед подсчётом
    clean_original = re.sub(r'\[NTP\]\d+', '', original)
    clean_translated = re.sub(r'\[NTP\]\d+', '', translated)
    
    orig_tags = re.findall(r'\{[^}]+\}', clean_original)
    trans_tags = re.findall(r'\{[^}]+\}', clean_translated)
    if len(orig_tags) != len(trans_tags):
        errors.append(f"tag_mismatch: {len(orig_tags)} vs {len(trans_tags)}")
    
    # 5. Проверка баланса { } скобок в переведённом тексте
    # Исключаем NTP из подсчёта
    open_braces = clean_translated.count('{')
    close_braces = clean_translated.count('}')
    if open_braces != close_braces:
        errors.append(f"unbalanced_braces: {open_braces} vs {close_braces}")

    # 6. Проверка баланса [ ] скобок в переведённом тексте (исключая NTP)
    open_brackets = clean_translated.count('[')
    close_brackets = clean_translated.count(']')
    # Учитываем что каждый [NTP0001] содержит одну открывающую и одну закрывающую
    ntp_count = len(re.findall(r'\[NTP\]\d+', clean_translated))
    open_brackets -= ntp_count
    close_brackets -= ntp_count
    if open_brackets != close_brackets:
        errors.append(f"unbalanced_brackets: {open_brackets} vs {close_brackets}")

    # 7. Кавычки
    trans_quotes = translated.count('"')
    if trans_quotes % 2 != 0:
        errors.append("unclosed_quotes")

    # 8. Переменные [var] — проверяем только реальные переменные RenPy
    # Исключаем NTP и пустые скобки
    orig_vars = re.findall(r'\[[a-zA-Z_][a-zA-Z0-9_]*\]', clean_original)
    trans_vars = re.findall(r'\[[a-zA-Z_][a-zA-Z0-9_]*\]', clean_translated)
    if len(orig_vars) != len(trans_vars):
        errors.append(f"variable_mismatch: {len(orig_vars)} vs {len(trans_vars)}")

    # 9. Проверка непустого перевода
    if not translated or len(translated.strip()) < 1:
        errors.append("empty_translation")

    is_valid = len(errors) == 0
    if not is_valid:
        logger.warning(f"⚠️ Ошибки целостности: {errors} | text: {translated[:80]}")

    return is_valid, errors


class IntegrityChecker:
    """Проверяет целостность перевода после обработки."""

    def __init__(self):
        self.results: List[Dict] = []

    def check(self, original: str, translated: str, context: str = "") -> Dict:
        is_valid, errors = verify_translation_integrity(original, translated)
        result = {
            "context": context,
            "valid": is_valid,
            "errors": errors,
            "original_length": len(original),
            "translated_length": len(translated),
        }
        self.results.append(result)
        return result

    def get_summary(self) -> Dict:
        total = len(self.results)
        valid = sum(1 for r in self.results if r["valid"])
        return {
            "total_checked": total,
            "valid": valid,
            "failed": total - valid,
            "success_rate": round(valid / total * 100, 2) if total else 0,
        }
