"""
infrastructure/generators/language_registrar.py
Генератор файла регистрации языка для Ren'Py 8.x
Создаёт game/tl/russian/language.rpy с правильной регистрацией
Согласно PDF "Решение ключевых проблем локализации в Ren'Py"

Критически важно:
- init -1 python: выполняется ДО всех остальных init блоков
- renpy.add_language() регистрирует язык в меню настроек
- gui.text_font должен поддерживать кириллицу
"""
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LanguageRegistrar:
    """
    Создаёт game/tl/russian/language.rpy с правильной регистрацией языка
    Согласно PDF "Решение ключевых проблем локализации в Ren'Py"
    """
    
    # Стандартные коды языков ISO 639-1
    LANGUAGE_CODES = {
        'ru': 'Русский',
        'en': 'English',
        'ja': '日本語',
        'zh': '中文',
        'ko': '한국어',
        'fr': 'Français',
        'de': 'Deutsch',
        'es': 'Español',
        'pt': 'Português',
        'it': 'Italiano',
        'pl': 'Polski',
        'uk': 'Українська',
    }
    
    # Рекомендуемые шрифты с поддержкой кириллицы
    CYRILLIC_FONTS = [
        "fonts/NotoSansCJK-Regular.ttf",
        "fonts/DejaVuSans.ttf",
        "fonts/Arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    
    def __init__(self, game_path: Path):
        """
        Инициализирует регистратор языка
        
        Args:
            game_path: Путь к папке с игрой (где лежит game/)
        """
        self.game_path = game_path.resolve()
        self.tl_path = self.game_path / "game" / "tl" / "russian"
        self.language_file = self.tl_path / "language.rpy"
        self.style_file = self.tl_path / "style.rpy"
    
    def create(
        self,
        language_code: str = "russian",
        language_name: Optional[str] = None,
        font_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Создаёт файлы регистрации языка и настройки шрифтов
        
        Args:
            language_code: Код языка (ISO 639-1), например 'ru'
            language_name: Название языка для отображения в меню
            font_path: Путь к шрифту с поддержкой кириллицы
            
        Returns:
            (success: bool, message: str)
        """
        try:
            # Получаем название языка из кода, если не указано
            if language_name is None:
                language_name = self.LANGUAGE_CODES.get(
                    language_code,
                    language_code.upper()
                )
            
            # 1. Создаём директорию game/tl/russian/
            self.tl_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Создана директория: {self.tl_path}")
            
            # 2. Создаём language.rpy с регистрацией языка
            language_content = self._generate_language_rpy(
                language_code,
                language_name
            )
            self.language_file.write_text(language_content, encoding='utf-8')
            logger.info(f"✅ Создан файл регистрации: {self.language_file}")
            
            # 3. Создаём style.rpy с настройкой шрифтов
            style_content = self._generate_style_rpy(font_path)
            self.style_file.write_text(style_content, encoding='utf-8')
            logger.info(f"✅ Создан файл стилей: {self.style_file}")
            
            return True, f"Язык '{language_name}' успешно зарегистрирован"
            
        except PermissionError as e:
            error_msg = f"❌ Ошибка доступа: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ Ошибка создания файлов: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def _generate_language_rpy(
        self,
        language_code: str,
        language_name: str
    ) -> str:
        """
        Генерирует содержимое language.rpy
        
        Критически важно: init -1 python: выполняется до всех остальных init блоков
        Это гарантирует максимально раннюю регистрацию языка
        """
        return f'''## game/tl/russian/language.rpy
## ============================================================================
## Файл регистрации языка для Ren'Py 8.x
## ============================================================================
## 
## Этот файл выполняется при запуске игры и регистрирует русский язык
## в меню настроек. Блок init -1 выполняется ДО всех остальных init блоков,
## что гарантирует корректную инициализацию до построения интерфейса.
##
## Источник: PDF "Решение ключевых проблем локализации в Ren'Py"
## ============================================================================

## Блок с приоритетом -1 выполняется до всех остальных init блоков
## Это гарантирует максимально раннюю регистрацию языка
init -1 python:
    # Регистрация русского языка
    # '{language_code}' — идентификатор языка (ISO 639-1)
    # "{language_name}" — название для отображения в меню настроек
    renpy.add_language('{language_code}', "{language_name}")
    
    # Логирование для отладки
    renpy.log("Language '{language_code}' ({language_name}) registered successfully")

## Опционально: можно добавить дополнительную инициализацию здесь
## Например, настройку специфичных для языка параметров
'''
    
    def _generate_style_rpy(self, font_path: Optional[str] = None) -> str:
        """
        Генерирует содержимое style.rpy с настройкой шрифтов
        
        Критически важно: gui.text_font должен поддерживать кириллицу
        Иначе вместо букв будут отображаться квадраты (□)
        """
        # Если шрифт не указан, используем первый из списка доступных
        if font_path is None:
            font_path = self._find_available_font()
        
        return f'''## game/tl/russian/style.rpy
## ============================================================================
## Настройка стилей для русского языка
## ============================================================================
##
## Этот файл настраивает шрифты и стили для корректного отображения
## кириллических символов. Без правильной настройки шрифта вместо
## русских букв будут отображаться квадраты (□).
##
## Источник: PDF "Решение ключевых проблем локализации в Ren'Py"
## ============================================================================

## Настройка шрифта для основного текста
## Используем init -1 для применения до загрузки интерфейса
init -1 python:
    # ✅ Критически важно: gui.text_font вместо устаревшего config.text_font
    # Путь к шрифту с поддержкой кириллицы
    gui.text_font = "{font_path}"
    
    # Опционально: настройка шрифта для имен персонажей
    # gui.name_text_font = "{font_path}"
    
    # Опционально: настройка шрифта для интерфейса
    # gui.interface_text_font = "{font_path}"
    
    # Логирование для отладки
    renpy.log(f"Font configured: {{gui.text_font}}")

## Настройка размеров текста (русский текст обычно длиннее английского)
style default:
    # Увеличиваем размер шрифта для лучшей читаемости
    # size 22 подходит для большинства игр
    size 22
    
    # Межстрочный интервал
    line_spacing 2

style say_label:
    # Шрифт для имен персонажей в диалогах
    font "{font_path}"
    size 24
    bold True

style say_dialogue:
    # Шрифт для текста диалогов
    font "{font_path}"
    size 22
    line_spacing 2

## Опционально: настройка кнопок меню
style button_text:
    font "{font_path}"
    size 20

## Опционально: настройка заголовков
style label_text:
    font "{font_path}"
    size 28
    bold True
'''
    
    def _find_available_font(self) -> str:
        """
        Ищет первый доступный шрифт с поддержкой кириллицы
        
        Returns:
            Путь к первому найденному шрифту или путь по умолчанию
        """
        for font_path in self.CYRILLIC_FONTS:
            # Проверяем разные варианты путей
            paths_to_check = [
                self.game_path / font_path,
                Path(font_path),
            ]
            
            for path in paths_to_check:
                if path.exists():
                    logger.info(f"✅ Найден шрифт: {path}")
                    # Возвращаем относительный путь для Ren'Py
                    try:
                        return str(path.relative_to(self.game_path))
                    except ValueError:
                        return str(path)
        
        # Если ни один шрифт не найден, возвращаем путь по умолчанию
        logger.warning("⚠️ Шрифт не найден, используем путь по умолчанию")
        return "fonts/NotoSansCJK-Regular.ttf"
    
    def verify(self) -> Tuple[bool, list]:
        """
        Проверяет наличие и корректность файлов регистрации
        
        Returns:
            (is_valid: bool, issues: list)
        """
        issues = []
        
        # 1. Проверяем наличие директории
        if not self.tl_path.exists():
            issues.append(f"❌ Директория не найдена: {self.tl_path}")
            return False, issues
        
        # 2. Проверяем language.rpy
        if not self.language_file.exists():
            issues.append(f"❌ Файл language.rpy не найден: {self.language_file}")
        else:
            content = self.language_file.read_text(encoding='utf-8')
            
            # Проверяем наличие renpy.add_language
            if "renpy.add_language" not in content:
                issues.append("❌ В language.rpy отсутствует renpy.add_language()")
            
            # Проверяем init -1 (критично!)
            if "init -1 python:" not in content:
                issues.append("❌ В language.rpy отсутствует init -1 python (критично!)")
            else:
                issues.append("✅ init -1 python: найден")
        
        # 3. Проверяем style.rpy
        if not self.style_file.exists():
            issues.append(f"⚠️ Файл style.rpy не найден: {self.style_file}")
        else:
            content = self.style_file.read_text(encoding='utf-8')
            
            # Проверяем gui.text_font
            if "gui.text_font" not in content:
                issues.append("❌ В style.rpy отсутствует gui.text_font")
            else:
                issues.append("✅ gui.text_font настроен")
        
        is_valid = len([i for i in issues if i.startswith("❌")]) == 0
        return is_valid, issues
    
    def clear_cache(self) -> bool:
        """
        Очищает кэш Ren'Py для применения изменений
        
        Returns:
            True если успешно
        """
        cache_path = self.game_path / "game" / "cache"
        
        try:
            if cache_path.exists():
                for file in cache_path.glob("*"):
                    if file.is_file():
                        file.unlink()
                logger.info(f"✅ Кэш очищен: {cache_path}")
                return True
            else:
                logger.info("ℹ️ Кэш не найден, очистка не требуется")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша: {e}")
            return False
    
    def get_language_info(self) -> dict:
        """
        Возвращает информацию о зарегистрированном языке
        
        Returns:
            dict с информацией о языке
        """
        is_valid, issues = self.verify()
        
        return {
            'language_code': 'ru',
            'language_name': 'Русский',
            'tl_path': str(self.tl_path),
            'language_file': str(self.language_file),
            'style_file': str(self.style_file),
            'is_valid': is_valid,
            'issues': issues,
            'exists': self.tl_path.exists()
        }