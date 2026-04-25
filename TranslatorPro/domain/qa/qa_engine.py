"""
QAEngine — проверка качества перевода
ИСПРАВЛЕНО: __name__, добавлена проверка §§VAR_...§§ (Ren'Py compiled format)
Согласно PDF "Решение ключевых проблем локализации в Ren'Py"
"""
import re
from typing import Dict, List
import logging

# ✅ ИСПРАВЛЕНО: __name__ вместо name
logger = logging.getLogger(__name__)


class QAEngine:
    """Движок проверки качества перевода"""
    
    def __init__(self):
        self.max_length_ratio = 4
        self.repeated_chars_threshold = 20
        # ✅ Ren'Py compiled placeholder pattern (§§VAR_...§§)
        self.renpy_placeholder_pattern = re.compile(r'§§VAR_[^§]+§§')
        # ✅ Glossary placeholder pattern
        self.glossary_placeholder_pattern = re.compile(r'###TERM_[a-f0-9]{8}###')
        # ✅ Protection placeholder pattern
        self.protection_placeholder_pattern = re.compile(r'###PH\d+###')

    def check(self, original: str, translated: str) -> Dict:
        """Проверяет качество перевода"""
        issues: List[str] = []
        
        # 1. Пустой перевод
        if len(translated.strip()) < 1:
            issues.append("empty_translation")
        
        # 2. Слишком длинный перевод
        elif len(translated) > len(original) * self.max_length_ratio:
            issues.append("too_long")
        
        # 3. Проверка баланса скобок {} — ИСКЛЮЧАЕМ RenPy теги и NTP из подсчёта
        # Очищаем от NTP плейсхолдеров для точного подсчёта
        clean_orig = self.renpy_placeholder_pattern.sub('', original)
        clean_orig = re.sub(r'\[NTP\]\d+', '', clean_orig)
        clean_trans = self.renpy_placeholder_pattern.sub('', translated)
        clean_trans = re.sub(r'\[NTP\]\d+', '', clean_trans)
        
        if clean_orig.count('{') != clean_trans.count('{'):
            issues.append("brace_mismatch")
        if clean_orig.count('}') != clean_trans.count('}'):
            issues.append("brace_mismatch")
        
        # 4. Проверка баланса скобок [] — ИСКЛЮЧАЕМ RenPy переменные и NTP
        if clean_orig.count('[') != clean_trans.count('['):
            issues.append("bracket_mismatch")
        if clean_orig.count(']') != clean_trans.count(']'):
            issues.append("bracket_mismatch")
        
        # 5. Проверка кавычек
        if translated.count('"') % 2 != 0:
            issues.append("unclosed_quotes")
        
        # 6. ✅ ИСПРАВЛЕНО: Проверка Ren'Py плейсхолдеров §§VAR_...§§
        orig_vars = self.renpy_placeholder_pattern.findall(original)
        trans_vars = self.renpy_placeholder_pattern.findall(translated)
        if len(orig_vars) != len(trans_vars):
            issues.append("renpy_variable_mismatch")
            logger.warning(
                f"Placeholder mismatch: original={len(orig_vars)}, translated={len(trans_vars)}"
            )
        
        # 7. Проверка глоссария (не должно остаться в переводе)
        if self.glossary_placeholder_pattern.search(translated):
            issues.append("unrestored_glossary_term")
        
        # 8. Проверка защиты (не должно остаться в переводе)
        if self.protection_placeholder_pattern.search(translated):
            issues.append("unrestored_placeholder")
        
        # 8b. ❌ Оставшиеся NTP плейсхолдеры в переводе (критично)
        if re.search(r'\[NTP\]\d+', translated):
            issues.append("unrestored_ntp")
        
        # 8c. ❌ Оставшиеся ###PH_### маркеры в переводе (критично)
        if re.search(r'###PH_\d+###', translated):
            issues.append("unrestored_ph")
        
        # 9. Проверка на повторения символов
        if re.search(r'(.)\1{' + str(self.repeated_chars_threshold) + r',}', translated):
            issues.append("repeated_chars")
        
        # 10. ✅ Если в оригинале есть VAR-плейсхолдеры, они должны быть в переводе
        if orig_vars and not trans_vars:
            issues.append("lost_renpy_variables")
            logger.error(f"Lost all Ren'Py variables in translation: {original[:50]}...")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "score": max(0, 100 - len(issues) * 15)
        }