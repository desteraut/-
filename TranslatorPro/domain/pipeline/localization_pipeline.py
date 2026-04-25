"""
LocalizationPipeline V7 — Главный оркестратор
ИСПРАВЛЕНО V7:
  - CodeProtector теперь использует is_code=False для диалогов (не трогает and/in/.)
  - Убрана Unicode PUA защита — ArgosEngine сам защищает плейсхолдеры через @@NTP@@
  - Добавлена валидация перевода: проверка на кириллицу для русского языка
  - Не сохраняем в кэш проваленные переводы
  - Если движок не перевёл — возвращаем оригинал
"""
from typing import Callable, Optional, List, Dict
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


class LocalizationPipeline:
    """Оркестратор процесса локализации V7"""
    
    def __init__(self, code_guard, protection_manager, quote_guard,
                 cache, glossary, qa, engines, post_processor=None,
                 integrity_checker=None, text_fitter=None,
                 code_protector=None,
                 src_lang: str = "en", tgt_lang: str = "russian"):
        self.code_guard = code_guard
        self.protection_manager = protection_manager
        self.quote_guard = quote_guard
        self.cache = cache
        self.glossary = glossary
        self.qa = qa
        self.post_processor = post_processor
        self.integrity_checker = integrity_checker
        self.text_fitter = text_fitter
        self.code_protector = code_protector
        
        self.engines = engines
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        
        self.progress_callback: Optional[Callable[[int, int], None]] = None
        self.current = 0
        self.total = 0
        
        # Для валидации русского перевода
        self._cyrillic_pattern = re.compile(r'[\u0400-\u04FF\u0500-\u052F]')
        self._min_cyrillic_ratio = 0.15  # Минимум 15% кириллицы для русского

    def set_progress_callback(self, callback: Callable[[int, int], None]):
        self.progress_callback = callback

    def _notify_progress(self):
        if self.progress_callback:
            self.progress_callback(self.current, self.total)

    def _is_actually_translated(self, original: str, translated: str) -> bool:
        """
        Проверяет, действительно ли текст переведён.
        Для русского: должен содержать кириллические символы.
        """
        if not translated or translated.strip() == "":
            return False
        
        if translated == original:
            return False
        
        # Для русского языка проверяем наличие кириллицы
        if self.tgt_lang.lower() in ("russian", "ru"):
            cyrillic_chars = len(self._cyrillic_pattern.findall(translated))
            total_chars = len(translated.strip())
            if total_chars > 0:
                ratio = cyrillic_chars / total_chars
                if ratio < self._min_cyrillic_ratio:
                    logger.warning(
                        f"Перевод отклонён: недостаточно кириллицы "
                        f"({ratio:.1%} < {self._min_cyrillic_ratio:.0%}). "
                        f"Текст: {translated[:60]}..."
                    )
                    return False
        
        return True

    def translate(self, text: str, filename: str = "unknown",
                  line_num: int = 0, speaker: str = None,
                  item_type: str = "dialogue") -> str:
        """Полный процесс перевода одной строки V7"""
        
        if not text or text.strip() == "":
            return text
        
        if self.code_guard.is_code_line(text):
            return text
        
        # Передаём версии в кэш
        glossary_version = str(self.glossary.get_terms_count())
        engine_model_version = "argos-1.9"
        
        cached = self.cache.get_translation(
            text, self.src_lang, self.tgt_lang, filename, line_num,
            glossary_version=glossary_version,
            engine_model_version=engine_model_version
        )
        if cached:
            logger.debug(f"Кэш hit: {text[:50]}...")
            cached_text = cached.get('translated_text', text)
            # Проверяем, что кэшированный перевод действительно переведён
            if self._is_actually_translated(text, cached_text):
                return cached_text
            else:
                logger.warning(f"Кэш содержит плохой перевод, переводим заново: {text[:50]}...")
        
        logger.debug(f"Кэш miss: {text[:50]}...")
        
        original_text = text
        engine_used = None
        
        # 1. Защита кода [NTP:x] (m06_code_protector)
        # ✅ ИСПРАВЛЕНО: для диалогов используем is_code=False
        is_code = item_type not in ("dialogue", "menu")
        if self.code_protector:
            protected_text = self.code_protector.protect(text, is_code=is_code)
        else:
            protected_text = text
        
        # 2. Защита переменных и тегов [var] {tag} (старая система)
        protected_text = self.protection_manager.protect(protected_text)
        
        # 3. Применение глоссария (ПЕРЕД переводом)
        safe_text = self.glossary.apply(protected_text, direction="pre")
        
        # 4. Перевод через доступный движок
        translated = None
        for engine in self.engines:
            if engine.is_available():
                try:
                    result = engine.translate(safe_text)
                    if result and result.strip():
                        translated = result
                        engine_used = engine.get_name()
                        break
                except Exception as e:
                    logger.error(f"Ошибка движка {engine.get_name()}: {e}")
                    continue
        
        # Если ни один движок не перевёл — возвращаем оригинал
        if translated is None:
            logger.warning(f"[{filename}:{line_num}] Ни один движок не перевёл, возвращаем оригинал")
            return original_text
        
        # 5. Восстанавливаем глоссарий (ПОСЛЕ перевода)
        with_glossary = self.glossary.apply(translated, direction="post")
        
        # 6. Восстанавливаем переменные и теги [var] {tag}
        with_protected = self.protection_manager.restore(with_glossary)
        
        # 7. Восстанавливаем [NTP:x] плейсхолдеры
        if self.code_protector:
            with_protected = self.code_protector.restore(with_protected)
        
        # 8. Пост-обработка (кавычки → ёлочки, многоточие и т.д.)
        escaped_text = with_protected
        if self.post_processor:
            escaped_text = self.post_processor.process(escaped_text)
        
        # 9. Экранирование кавычек
        escaped_text = self.quote_guard.escape_for_renpy(escaped_text)
        
        # 10. Адаптация длины текста
        if self.text_fitter:
            escaped_text = self.text_fitter.process_translation(escaped_text)
        
        # 11. Проверяем, действительно ли переведено
        if not self._is_actually_translated(original_text, escaped_text):
            logger.warning(
                f"[{filename}:{line_num}] Перевод не прошёл валидацию, возвращаем оригинал. "
                f"Результат: {escaped_text[:60]}..."
            )
            return original_text
        
        # 12. QA проверки
        qa_result = self.qa.check(original_text, escaped_text)
        
        # 13. Проверка целостности
        if self.integrity_checker:
            integrity_result = self.integrity_checker.check(original_text, escaped_text, f"{filename}:{line_num}")
            if not integrity_result.get("valid", True):
                logger.warning(f"[{filename}:{line_num}] Integrity check failed: {integrity_result.get('errors', [])}")
        
        if not qa_result.get("valid", True):
            logger.warning(f"[{filename}:{line_num}] QA проблемы: {qa_result.get('issues', [])}")
        
        # Сохраняем в кэш ТОЛЬКО если перевод действительно прошёл валидацию
        self.cache.save_translation(
            original_text, escaped_text, self.src_lang, self.tgt_lang,
            filename, line_num,
            speaker=speaker,
            item_type=item_type,
            engine_name=engine_used or "unknown",
            glossary_version=glossary_version,
            engine_model_version=engine_model_version,
            qa_result=qa_result
        )
        
        self.current += 1
        self._notify_progress()
        
        return escaped_text
    
    def translate_batch(self, texts: List[Dict], filename: str = "unknown") -> List[Dict]:
        """Переводит пакет строк с прогрессом"""
        self.total = len(texts)
        self.current = 0
        results = []
        
        for i, item in enumerate(texts):
            text = item.get("text", "")
            line_num = item.get("line", 0)
            file_name = item.get("file", filename)
            speaker = item.get("speaker")
            item_type = item.get("type", "dialogue")
            
            translated = self.translate(text, file_name, line_num, speaker=speaker, item_type=item_type)
            results.append({
                **item,
                "translated": translated
            })
        
        return results

    def clear_cache(self):
        self.cache.clear_cache()
        logger.info("🗑️ Кэш очищен")

    def get_cache_stats(self) -> Dict:
        return self.cache.get_stats()
