#!/usr/bin/env python3
"""
translatorpro_cli.py — CLI-версия TranslatorPro V3
Позволяет запускать перевод из командной строки без GUI.

ИСПОЛЬЗОВАНИЕ:
    python translatorpro_cli.py <путь_к_игре> [--lang russian] [--mock]

Пример:
    python translatorpro_cli.py ./game
    python translatorpro_cli.py ./game --mock  # для теста без Argos
"""
import argparse
import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TranslatorProCLI")

# Добавляем путь к модулям проекта
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.extractors.renpy_extractor import RenPyExtractor
from infrastructure.generators.renpy_generator import RenPyGenerator
from infrastructure.guards.code_guard import CodeGuard
from infrastructure.guards.protection_manager import ProtectionManager
from infrastructure.guards.quote_guard import QuoteGuard
from infrastructure.cache.sqlite_cache import SQLiteCache
from domain.glossary.glossary_manager import GlossaryManager
from domain.qa.qa_engine import QAEngine
from domain.pipeline.localization_pipeline import LocalizationPipeline
from modules.m06_code_protector import CodeProtector
from modules.m08_text_fitter import TextFitter
from modules.m09_font_manager import FontManager
from modules.m10_post_processor import PostProcessor
from modules.m11_integrity_checker import IntegrityChecker
from modules.m12_report_generator import ReportGenerator
from infrastructure.engines.argos_engine import ArgosEngine


class MockEngine:
    """Тестовый движок для проверки пайплайна без Argos."""
    def __init__(self, src="en", tgt="russian"):
        self.src = src
        self.tgt = tgt
        self._available = True
        self.name = "MockEngine"
    def is_available(self):
        return self._available
    def get_name(self):
        return self.name
    def translate(self, text):
        if not text or not text.strip():
            return text
        return text + " [переведено-на-русский]"


def run_translation(game_dir: Path, use_mock: bool = False, language: str = "russian"):
    """Запускает полный цикл перевода."""
    logger.info(f"=== TranslatorPro V3 CLI ===")
    logger.info(f"Игра: {game_dir}")
    logger.info(f"Язык: {language}")
    logger.info(f"Движок: {'MockEngine (тест)' if use_mock else 'ArgosTranslate'}")

    # 1. Извлечение
    logger.info("[1/4] Извлечение текста...")
    extractor = RenPyExtractor(str(game_dir))
    texts = extractor.extract_all()
    logger.info(f"  Извлечено {len(texts)} строк")
    
    if not texts:
        logger.error("  Нет текста для перевода!")
        return False

    # 2. Инициализация компонентов
    cache_db = game_dir / f"translatorpro_cache_{language}.db"
    cache = SQLiteCache(cache_db)
    code_guard = CodeGuard()
    protection_manager = ProtectionManager()
    quote_guard = QuoteGuard()
    glossary = GlossaryManager()
    qa = QAEngine()
    code_protector = CodeProtector()
    post_processor = PostProcessor()
    integrity_checker = IntegrityChecker()
    text_fitter = TextFitter()

    if use_mock:
        engines = [MockEngine()]
    else:
        argos = ArgosEngine()
        if not argos.is_available():
            logger.error("  Argos Translate недоступен! Используйте --mock для теста.")
            return False
        engines = [argos]

    pipeline = LocalizationPipeline(
        code_guard=code_guard,
        protection_manager=protection_manager,
        quote_guard=quote_guard,
        cache=cache,
        glossary=glossary,
        qa=qa,
        engines=engines,
        post_processor=post_processor,
        integrity_checker=integrity_checker,
        text_fitter=text_fitter,
        code_protector=code_protector,
        src_lang="en",
        tgt_lang=language
    )

    # 3. Перевод
    logger.info("[2/4] Перевод...")
    results = pipeline.translate_batch(texts)
    
    success = sum(1 for r in results if r.get('translated') and r.get('translated') != r.get('text'))
    failed = len(results) - success
    logger.info(f"  Успешно: {success}/{len(results)}")
    logger.info(f"  Пропущено: {failed}/{len(results)}")

    # 4. Генерация
    logger.info("[3/4] Генерация файлов...")
    generator = RenPyGenerator(cache=cache, language_code=language)
    output_dir = generator.generate_language_pack(game_dir, translations_data=results)
    logger.info(f"  Языковой пакет: {output_dir}")

    # 5. Отчёт
    logger.info("[4/4] Отчёт...")
    rpy_files = list(output_dir.glob("*.rpy"))
    total_blocks = 0
    for rpy_file in rpy_files:
        content = rpy_file.read_text(encoding='utf-8')
        blocks = content.split(f'translate {language} ')
        total_blocks += max(0, len(blocks) - 1)
    
    logger.info(f"  Создано файлов: {len(rpy_files)}")
    logger.info(f"  Всего блоков: {total_blocks}")
    logger.info(f"  Кэш: {cache_db}")
    
    logger.info("=== ГОТОВО ===")
    return True


def main():
    parser = argparse.ArgumentParser(description="TranslatorPro V3 — CLI перевод Ren'Py игр")
    parser.add_argument("game_dir", help="Путь к папке с игрой (где лежит папка game/)")
    parser.add_argument("--lang", default="russian", help="Целевой язык (default: russian)")
    parser.add_argument("--mock", action="store_true", help="Использовать тестовый движок вместо Argos")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить количество строк для теста")
    
    args = parser.parse_args()
    
    game_path = Path(args.game_dir).resolve()
    if not game_path.exists():
        logger.error(f"Папка не найдена: {game_path}")
        sys.exit(1)
    
    success = run_translation(game_path, use_mock=args.mock, language=args.lang)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
