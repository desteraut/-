"""
Модули TranslatorPro V3 (refactored).

Удалены:
- m01_logger.py -> используйте infrastructure.utils.logger / error_logger
- m04_rpyc_decompiler.py -> .rpyc поддержка удалена
- m05_text_extractor.py -> используйте infrastructure.extractors.renpy_extractor
- m07_translator.py -> используйте infrastructure.engines

Оставшиеся модули:
- m02_project_manager: Управление проектами .rtp
- m03_rpa_extractor: Распаковка .rpa архивов (wrapper)
- m06_code_protector: Защита кода [NTP:x] плейсхолдерами
- m08_text_fitter: Адаптация длины переведённого текста
- m09_font_manager: Проверка и замена шрифтов
- m10_post_processor: Пост-обработка (кавычки, многоточие)
- m11_integrity_checker: Проверка целостности перевода
- m12_report_generator: Генерация отчётов
"""

from .m02_project_manager import ProjectManager
from .m03_rpa_extractor import RPAExtractor
from .m06_code_protector import CodeProtector
from .m08_text_fitter import TextFitter
from .m09_font_manager import FontManager
from .m10_post_processor import PostProcessor
from .m11_integrity_checker import IntegrityChecker
from .m12_report_generator import ReportGenerator

__all__ = [
    'ProjectManager',
    'RPAExtractor',
    'CodeProtector',
    'TextFitter',
    'FontManager',
    'PostProcessor',
    'IntegrityChecker',
    'ReportGenerator',
]
