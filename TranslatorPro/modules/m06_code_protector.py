"""
m06_code_protector.py — Защита Ren'Py/Python-кода от перевода
ИСПРАВЛЕНО V3: Только кодовые конструкции, НЕ трогаем обычные слова естественного языка
"""
import re
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CodeProtector:
    """
    Защита кода плейсхолдерами [NTP:x] (Non-Translatable Placeholders).
    
    ✅ ИСПРАВЛЕНО V3: Разделение на DIALOGUE и CODE режимы.
    Для диалогов защищаем ТОЛЬКО RenPy теги, переменные, пути, HTML.
    Для кода (screen, init python) защищаем также ключевые слова и операторы.
    """
    
    # Паттерны для ДИАЛОГОВ и строк интерфейса (естественный язык)
    # НЕ трогаем: and, or, in, not, is, True, False, точки, и т.д.
    DIALOGUE_PATTERNS: List[Tuple[str, str, str]] = [
        # 1. Комментарии Python и Ren'Py
        (r'\s*##\s+.*', '[NTP]', 'renpy_comment'),
        (r'\s*#\s+.*', '[NTP]', 'python_comment'),
        
        # 2. Пути к ресурсам (только в кавычках — явно путь)
        (r'"[A-Za-z0-9_./\\-]+\.(?:png|jpg|jpeg|gif|bmp|webp|ogg|mp3|wav|avi|mkv|mp4|ttf|otf|woff|woff2|rpy|rpyc|json|xml|txt|csv|zip|7z|tar|gz)"', '[NTP]', 'resource_path'),
        
        # 3. HTML/XML теги
        (r'<[A-Za-z][^>]*>', '[NTP]', 'html_tag'),
        (r'</[A-Za-z]+>', '[NTP]', 'html_close'),
        (r'<!--.*?-->', '[NTP]', 'html_comment'),
        (r'\{\{.*?\}\}', '[NTP]', 'django_var'),
        (r'\{%.*?%\}', '[NTP]', 'django_tag'),
        
        # 4. Ren'Py теги — единый маркер
        (r'\{/\w+\}', '[NTP]', 'renpy_tag_close'),
        (r'\{\w+=[^}]+\}', '[NTP]', 'renpy_tag_with_value'),
        (r'\{\w+\}', '[NTP]', 'renpy_tag_simple'),
        
        # 5. Escape-последовательности
        (r'\\[nrt]', '[NTP]', 'escape'),
        (r'\\[0-7]{1,3}', '[NTP]', 'escape_octal'),
        (r'\\x[0-9a-fA-F]{2}', '[NTP]', 'escape_hex'),
        (r'\\u[0-9a-fA-F]{4}', '[NTP]', 'escape_unicode'),
        (r'\\N\{[A-Za-z0-9\s]+\}', '[NTP]', 'escape_named'),
        
        # 6. Специфичные RenPy API вызовы (только если они ВНЕ диалога — редко)
        # Но оставляем на случай screen-текстов
        (r'renpy\.(?:pause|random|notify|display_menu|input|choice|screens|scene|show|hide|with|music|sound|voice|transition|event|rollback|jump|call|return|screen|predict|image|transform)\b', '[NTP]', 'renpy_api'),
    ]
    
    # Паттерны для КОДА (screen, init, python blocks)
    # Здесь можно агрессивно защищать ключевые слова
    CODE_PATTERNS: List[Tuple[str, str, str]] = [
        *DIALOGUE_PATTERNS,
        
        # Python строковые модификаторы
        (r'\b(u|ur|b|br|r)\b', '[NTP]', 'string_modifier'),
        
        # Python операторы и ключевые слова
        (r'\+\+|--', '[NTP]', 'inc_dec'),
        (r'[\/\*%-+\&\|\~^!<>=]+', '[NTP]', 'operators'),
        (r'[\/\*%-+\&\|\~^!<>=]+=', '[NTP]', 'assign_ops'),
        (r'\b(if|else|elif|while|for|in|return|def|class|try|except|finally|with|as|import|from|raise|assert|break|continue|pass|lambda|yield|await|async|global|nonlocal|del)\b', '[NTP]', 'keywords'),
        (r'\b(True|False|None)\b', '[NTP]', 'bool_none'),
        (r'\b(in|not in|is|is not|and|or|not)\b', '[NTP]', 'bool_ops'),
        
        # Ren'Py UI директивы
        (r'\b(imagebutton|button|textbutton|hotspot|bar|vbar|viewport|fixed|grid|side|imagemap)\b', '[NTP]', 'ui_elements'),
        (r'\b(keyboard|mouse|timer|key|action|event)\b', '[NTP]', 'ui_events'),
        (r'\baction\b|\bhovered\b|\bunhovered\b', '[NTP]', 'ui_actions'),
        
        # Свойства стиля Ren'Py
        (r'xpos\s+|ypos\s+|xalign\s+|yalign\s+', '[NTP]', 'style_pos'),
        (r'xmaximum\s+|ymaximum\s+|xminimum\s+|yminimum\s+', '[NTP]', 'style_size'),
        (r'xfill\s+|yfill\s+', '[NTP]', 'style_fill'),
        (r'spacing\s+|first_spacing\s+|xspacing\s+|yspacing\s+', '[NTP]', 'style_spacing'),
        (r'xysize\s+|xsize\s+|ysize\s+', '[NTP]', 'style_xysize'),
        
        # API Ren'Py (расширенный)
        (r'renpy\.transition\(', '[NTP]', 'renpy_transition'),
        (r'renpy\.show_screen\(', '[NTP]', 'renpy_show_screen'),
        (r'renpy\.hide_screen\(', '[NTP]', 'renpy_hide_screen'),
        (r'renpy\.call_in_new_context\(', '[NTP]', 'renpy_call_context'),
        (r'renpy\.invoke_in_new_context\(', '[NTP]', 'renpy_invoke'),
        (r'renpy\.curry\(', '[NTP]', 'renpy_curry'),
        (r'renpy\.store\.', '[NTP]', 'renpy_store'),
        (r'\bFunction\(', '[NTP]', 'Function'),
        (r'\bJump\(', '[NTP]', 'Jump'),
        (r'\bReturn\(', '[NTP]', 'Return'),
        (r'\bSetScreenVariable\(', '[NTP]', 'SetScreenVariable'),
        (r'\bSetLocalVariable\(', '[NTP]', 'SetLocalVariable'),
        (r'\bToggleScreenVariable\(', '[NTP]', 'ToggleScreenVariable'),
        (r'\bSelectedIf\(', '[NTP]', 'SelectedIf'),
        (r'\bSensitiveIf\(', '[NTP]', 'SensitiveIf'),
        
        # Python-выражения после $
        (r'\$(\s+\w+\s*=)', '[NTP]', 'py_assign'),
        (r'\$(\s*\w+\.\w+\s*\()', '[NTP]', 'py_method_call'),
        (r'\$(\s*renpy\.)', '[NTP]', 'py_renpy'),
        (r'\$(\s*store\.\w+\s*=)', '[NTP]', 'py_store'),
        (r'\$(\s*\w+\s*[\+\-*/%]=)', '[NTP]', 'py_augmented'),
        (r'\$(\s*\w+\s*=[^"\']*\d+)', '[NTP]', 'py_num_assign'),
        (r'\$(\s*\[.*?\])', '[NTP]', 'py_list'),
        (r'\$(\s*\{.*?\})', '[NTP]', 'py_dict'),
        (r'\$(\s*\w+\s*=[^"\']*(True|False|None))', '[NTP]', 'py_bool_assign'),
        
        # Точка (атрибуты Python) — только внутри выражений, НЕ в конце предложений
        # ИСПРАВЛЕНО: требуем букву с обеих сторон (атрибут)
        (r'\b\w+\b\.\b\w+\b', '[NTP]', 'dot_attr'),
    ]
    
    def __init__(self):
        self.placeholders: Dict[str, str] = {}
        self._counter = 0
    
    def _next_placeholder(self, marker: str) -> str:
        """Генерирует уникальный плейсхолдер [NTP0001]"""
        self._counter += 1
        return f"{marker}{self._counter:04d}"
    
    def protect(self, text: str, is_code: bool = False) -> str:
        """
        Защищает кодовые конструкции в тексте.
        
        Args:
            text: Текст для защиты
            is_code: Если True — использовать агрессивные CODE_PATTERNS (для screen/init).
                     Если False — использовать DIALOGUE_PATTERNS (для диалогов).
        """
        if not text:
            return text
        
        self.placeholders = {}
        self._counter = 0
        protected = text
        
        patterns = self.CODE_PATTERNS if is_code else self.DIALOGUE_PATTERNS
        
        for pattern, marker, category in patterns:
            try:
                def replace_match(match):
                    original = match.group(0)
                    ph = self._next_placeholder(marker)
                    self.placeholders[ph] = original
                    return ph
                
                protected = re.sub(pattern, replace_match, protected)
            except re.error as e:
                logger.warning(f"Ошибка regex в паттерне {category}: {e}")
                continue
        
        if self.placeholders:
            logger.debug(f"Защищено {len(self.placeholders)} конструкций в тексте (is_code={is_code})")
        return protected
    
    def restore(self, text: str) -> str:
        """
        Восстанавливает оригинальные конструкции из плейсхолдеров.
        """
        if not text or not self.placeholders:
            return text
        
        restored = text
        
        # Сортируем по длине плейсхолдера (от длинных к коротким)
        for ph in sorted(self.placeholders.keys(), key=len, reverse=True):
            original = self.placeholders[ph]
            restored = restored.replace(ph, original)
        
        return restored
    
    def protect_batch(self, texts: List[str], is_code: bool = False) -> List[str]:
        """Защищает список текстов"""
        return [self.protect(t, is_code=is_code) for t in texts]
    
    def restore_batch(self, texts: List[str]) -> List[str]:
        """Восстанавливает список текстов"""
        return [self.restore(t) for t in texts]
    
    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику защиты"""
        stats = {}
        for ph in self.placeholders:
            marker = ph.split('_')[0]
            stats[marker] = stats.get(marker, 0) + 1
        return stats
