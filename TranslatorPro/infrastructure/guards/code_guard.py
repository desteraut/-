"""
CodeGuard — защита ключевых слов Python и Ren'Py от перевода
"""
from typing import Set, List
import re


class CodeGuard:
    """Защищает ключевые слова Python и Ren'Py от перевода"""
    
    # Python ключевые слова
    PYTHON_KEYWORDS_CONTROL: Set[str] = {
        'if', 'else', 'elif', 'for', 'while', 'break', 'continue',
        'return', 'pass', 'yield', 'raise', 'try', 'except', 'finally',
        'with', 'as', 'assert', 'del', 'import', 'from', 'global', 'nonlocal'
    }
    
    PYTHON_KEYWORDS_DECLARATION: Set[str] = {
        'def', 'class', 'lambda', 'async', 'await'
    }
    
    PYTHON_BUILTINS_PROTECTED: Set[str] = {
        'print', 'len', 'range', 'str', 'int', 'float', 'bool', 'list',
        'dict', 'set', 'tuple', 'type', 'isinstance', 'issubclass',
        'getattr', 'setattr', 'hasattr', 'callable', 'enumerate', 'zip',
        'map', 'filter', 'sorted', 'reversed', 'sum', 'min', 'max',
        'abs', 'round', 'pow', 'divmod', 'all', 'any', 'chr', 'ord',
        'repr', 'hash', 'id', 'dir', 'vars', 'locals', 'globals'
    }
    
    PYTHON_EXCEPTIONS: Set[str] = {
        'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError',
        'AttributeError', 'ImportError', 'ModuleNotFoundError', 'NameError',
        'UnboundLocalError', 'IOError', 'OSError', 'FileNotFoundError',
        'PermissionError', 'StopIteration', 'GeneratorExit', 'KeyboardInterrupt',
        'SystemExit', 'RuntimeError', 'NotImplementedError', 'AssertionError'
    }
    
    # Ren'Py директивы
    RENPY_DIRECTIVES_MAIN: Set[str] = {
        'init', 'python', 'image', 'scene', 'show', 'hide', 'call',
        'jump', 'menu', 'label', 'return', 'window', 'pause', 'play',
        'stop', 'queue', 'voice', 'music', 'sound', 'menu'
    }
    
    RENPY_DIRECTIVES_DECLARATION: Set[str] = {
        'define', 'default', 'layer', 'transform', 'style', 'screen',
        'use', 'vbox', 'hbox', 'grid', 'frame', 'viewport', 'textbutton',
        'input', 'timer', 'key', 'modal', 'on', 'event'
    }
    
    RENPY_SCREEN_ELEMENTS: Set[str] = {
        'text', 'image', 'button', 'bar', 'vbar', 'hbar', 'scrollbar',
        'viewport', 'area', 'add', 'drag', 'draggroup', 'hotspot',
        'imagbutton', 'fixed', 'box', 'side', 'matrix', 'flowbox'
    }
    
    RENPY_STYLE_PROPERTIES: Set[str] = {
        'xsize', 'ysize', 'xalign', 'yalign', 'xanchor', 'yanchor',
        'xoffset', 'yoffset', 'xmaximum', 'ymaximum', 'xminimum', 'yminimum',
        'width', 'height', 'top', 'bottom', 'left', 'right', 'padding',
        'spacing', 'margin', 'background', 'foreground', 'color', 'font',
        'size', 'bold', 'italic', 'underline', 'strikethrough'
    }
    
    RENPY_API_FUNCTIONS: Set[str] = {
        'renpy.say', 'renpy.jump', 'renpy.call', 'renpy.show', 'renpy.hide',
        'renpy.scene', 'renpy.pause', 'renpy.input', 'renpy.choice',
        'renpy.notify', 'renpy.log', 'renpy.save', 'renpy.load',
        'renpy.restart', 'renpy.quit', 'renpy.block_rollback',
        'renpy.register_undo', 'renpy.text', 'renpy.image'
    }
    
    RENPY_SPECIAL_VARS: Set[str] = {
        'persistent', 'config', 'gui', 'store', '_preferences',
        '_history', '_rollback', '_version', 'main_menu', 'quick_menu'
    }
    
    RENPY_STATE_PREFIXES: Set[str] = {
        'hover_', 'idle_', 'selected_', 'insensitive_', 'activated_',
        'focused_', 'unfocused_', 'pressed_', 'alternative_'
    }
    
    PYTHON_MAGIC_METHODS: Set[str] = {
        '__init__', '__str__', '__repr__', '__len__', '__getitem__',
        '__setitem__', '__delitem__', '__iter__', '__next__', '__call__',
        '__enter__', '__exit__', '__new__', '__del__', '__eq__', '__ne__',
        '__lt__', '__le__', '__gt__', '__ge__', '__hash__', '__bool__'
    }
    
    def __init__(self):
        """Инициализация защитника кода"""
        self.protected_keywords: Set[str] = self._build_protected_set()
    
    def _build_protected_set(self) -> Set[str]:
        """Создаёт объединённое множество защищённых слов"""
        protected = set()
        
        # Python
        protected.update(self.PYTHON_KEYWORDS_CONTROL)
        protected.update(self.PYTHON_KEYWORDS_DECLARATION)
        protected.update(self.PYTHON_BUILTINS_PROTECTED)
        protected.update(self.PYTHON_EXCEPTIONS)
        protected.update(self.PYTHON_MAGIC_METHODS)
        
        # Ren'Py
        protected.update(self.RENPY_DIRECTIVES_MAIN)
        protected.update(self.RENPY_DIRECTIVES_DECLARATION)
        protected.update(self.RENPY_SCREEN_ELEMENTS)
        protected.update(self.RENPY_STYLE_PROPERTIES)
        protected.update(self.RENPY_API_FUNCTIONS)
        protected.update(self.RENPY_SPECIAL_VARS)
        
        return protected
    
    def is_protected_keyword(self, word: str) -> bool:
        """Проверяет, является ли слово защищённым ключевым словом"""
        return word in self.protected_keywords
    
    def is_code_line(self, text: str) -> bool:
        """
        Проверяет, является ли строка кодом (а не диалогом)
        ЭТОТ МЕТОД ДОБАВЛЕН!
        """
        if not text or not text.strip():
            return True
        
        stripped = text.strip()
        
        # Проверка на комментарии
        if stripped.startswith('#'):
            return True
        
        # Проверка на ключевые слова в начале строки
        first_word = stripped.split()[0] if stripped.split() else ''
        
        # Убираем возможные префиксы и суффиксы (: . - +)
        clean_word = re.sub(r'^[:\.\-\+]+|[:\.\-\+]+$', '', first_word)
        
        if clean_word in self.protected_keywords:
            return True
        
        # Проверка на вызов функций с защищёнными именами
        func_pattern = re.compile(r'(\w+)\s*\(')
        for match in func_pattern.finditer(stripped):
            func_name = match.group(1)
            if func_name in self.protected_keywords:
                return True
        
        # Проверка на префиксы состояний Ren'Py
        for prefix in self.RENPY_STATE_PREFIXES:
            if stripped.startswith(prefix):
                return True
        
        return False
    
    def protect_string(self, text: str) -> str:
        """Защищает ключевые слова в строке, заменяя их маркерами"""
        result = text
        protected_words = []
        
        words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', text)
        
        for i, word in enumerate(words):
            if self.is_protected_keyword(word):
                marker = f"###PROTECTED_{i}###"
                result = result.replace(word, marker, 1)
                protected_words.append((marker, word))
        
        return result
    
    def restore_string(self, text: str, protected_words: List[tuple]) -> str:
        """Восстанавливает защищённые слова после перевода"""
        result = text
        for marker, original_word in protected_words:
            result = result.replace(marker, original_word)
        return result
    
    def get_protected_keywords_count(self) -> int:
        """Возвращает количество защищённых ключевых слов"""
        return len(self.protected_keywords)
    
    def get_protected_keywords_list(self) -> List[str]:
        """Возвращает список всех защищённых ключевых слов"""
        return sorted(list(self.protected_keywords))