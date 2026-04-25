"""
Централизованная конфигурация проекта TranslatorPro V3
Версия: 3.0.0 (Clean Architecture)
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# === ВЕРСИЯ ===
version = "3.0.0"
author = "TranslatorPro Team"

# === БАЗОВЫЕ ПУТИ ===
PROJECT_ROOT = Path(__file__).resolve().parent
BASE_DIR = Path.home() / ".translatorpro"
BASE_DIR.mkdir(exist_ok=True)

# === ПУТИ К ДАННЫМ ===
CACHE_DB = BASE_DIR / "translation_cache.db"
MODEL_CACHE_DIR = BASE_DIR / "models_cache"
MODEL_CACHE_DIR.mkdir(exist_ok=True)

# === ПУТИ К ФАЙЛАМ ПРОЕКТА ===
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "rusgameloc.log"
GLOSSARY_FILE = PROJECT_ROOT / "glossary.txt"
FONT_PATH = PROJECT_ROOT / "assets" / "fonts" / "DejaVuSans.ttf"
TEMPLATE_DIR = PROJECT_ROOT / "assets" / "templates"

# === ЯЗЫКОВЫЕ НАСТРОЙКИ ===
SOURCE_LANGUAGE = os.getenv("SOURCE_LANGUAGE", "en")
# ✅ ИСПРАВЛЕНО: TARGET_LANGUAGE теперь "russian" (имя папки RenPy tl/)
# ArgosEngine/NLLBEngine сами мапят на ISO коды при необходимости
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE", "russian")

# === НАСТРОЙКИ МОДЕЛЕЙ ===
USE_ARGOS = os.getenv("USE_ARGOS", "True").lower() == "true"
USE_NLLB = os.getenv("USE_NLLB", "False").lower() == "true"
USE_GPU = os.getenv("USE_GPU", "False").lower() == "true"

# === НАСТРОЙКИ ПЕРЕВОДА ===
CONTEXT_SIZE = int(os.getenv("CONTEXT_SIZE", "5"))
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "400"))

# === ЛИМИТЫ БЕЗОПАСНОСТИ ===
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))
DECOMPILER_TIMEOUT = int(os.getenv("DECOMPILER_TIMEOUT", "300"))
DECOMPILER_MAX_WORKERS = int(os.getenv("DECOMPILER_MAX_WORKERS", "4"))

# === НАСТРОЙКИ REN'PY ===
RENPY_TL_FOLDER = os.getenv("RENPY_TL_FOLDER", "russian")
RENPY_TL_PATH = f"game/tl/{RENPY_TL_FOLDER}/"

# === GUI НАСТРОЙКИ ===
GUI_THEME = os.getenv("GUI_THEME", "light")
GUI_LANGUAGE = os.getenv("GUI_LANGUAGE", "ru")

# === API КЛЮЧИ ===
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# === НАСТРОЙКИ ЛОГИРОВАНИЯ ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "10000000"))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# === НАСТРОЙКИ КЭША ===
CACHE_WAL_MODE = True
CACHE_TIMEOUT = 30