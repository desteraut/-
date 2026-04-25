"""
ArgosEngine — оффлайн переводчик на базе Argos Translate
ИСПРАВЛЕНО V3:
  - Корректная инициализация с тестовым переводом
  - Защита плейсхолдеров [NTP...] и ###PH_### через @@NTP@@
  - Обработка ошибок Stanza (sentence boundary detection)
  - Проверка доступности через реальный тестовый перевод
"""
from pathlib import Path
from typing import Optional
import logging
import re
import time

logger = logging.getLogger(__name__)


class ArgosEngine:
    """Движок перевода на базе Argos Translate"""
    
    def __init__(self, src_lang: str = "en", tgt_lang: str = "russian"):
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self._model = None
        self._available = None
        self._placeholder_counter = 0
        self._placeholder_map: dict = {}
        self.name = "Argos Translate"
        self._init_error: Optional[str] = None
    
    def _get_argos_lang_code(self, lang: str) -> str:
        """Маппинг языковых кодов проекта на ISO-коды Argos Translate."""
        mapping = {
            "russian": "ru",
            "english": "en",
            "french": "fr",
            "german": "de",
            "spanish": "es",
            "italian": "it",
            "portuguese": "pt",
            "chinese": "zh",
            "japanese": "ja",
            "korean": "ko",
            "polish": "pl",
            "turkish": "tr",
            "dutch": "nl",
            "arabic": "ar",
        }
        return mapping.get(lang.lower(), lang)
    
    def initialize(self) -> bool:
        """Инициализация движка с тестовым переводом"""
        try:
            return self._init_model()
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Argos: {e}")
            self._available = False
            self._init_error = str(e)
            return False
    
    def _protect_placeholders(self, text: str) -> str:
        """
        Защищает плейсхолдеры от перевода Argos.
        Заменяет [NTP...] и ###PH_### на неразрушимые маркеры @@NTP1@@.
        """
        self._placeholder_map = {}
        self._placeholder_counter = 0
        protected = text
        
        # Паттерн 1: [NTP0001]
        ntp_pattern = re.compile(r'\[NTP\]\d+')
        for match in ntp_pattern.finditer(protected):
            self._placeholder_counter += 1
            marker = f"@@NTP{self._placeholder_counter}@@"
            self._placeholder_map[marker] = match.group(0)
            protected = protected.replace(match.group(0), marker, 1)
        
        # Паттерн 2: ###PH_N###
        ph_pattern = re.compile(r'###PH_\d+###')
        for match in ph_pattern.finditer(protected):
            self._placeholder_counter += 1
            marker = f"@@PH{self._placeholder_counter}@@"
            self._placeholder_map[marker] = match.group(0)
            protected = protected.replace(match.group(0), marker, 1)
        
        # Паттерн 3: ###TERM_...###
        term_pattern = re.compile(r'###TERM_[a-f0-9]{8}###')
        for match in term_pattern.finditer(protected):
            self._placeholder_counter += 1
            marker = f"@@TERM{self._placeholder_counter}@@"
            self._placeholder_map[marker] = match.group(0)
            protected = protected.replace(match.group(0), marker, 1)
        
        return protected
    
    def _restore_placeholders(self, text: str) -> str:
        """Восстанавливает плейсхолдеры после перевода."""
        if not self._placeholder_map:
            return text
        restored = text
        for marker in sorted(self._placeholder_map.keys(), key=len, reverse=True):
            original = self._placeholder_map[marker]
            restored = restored.replace(marker, original)
        return restored
    
    def _init_model(self):
        """Инициализирует модель перевода с проверкой работоспособности"""
        try:
            import argostranslate.package
            import argostranslate.translate
            
            argos_src = self._get_argos_lang_code(self.src_lang)
            argos_tgt = self._get_argos_lang_code(self.tgt_lang)
            
            # Проверяем наличие пакетов
            installed_packages = argostranslate.package.get_installed_packages()
            
            ru_package = None
            for package in installed_packages:
                if package.from_code == argos_src and package.to_code == argos_tgt:
                    ru_package = package
                    break
            
            if not ru_package:
                logger.warning(f"⚠️ Пакет перевода {argos_src}->{argos_tgt} не найден. Установка...")
                try:
                    success = argostranslate.package.install_package_for_language_pair(
                        argos_src, argos_tgt
                    )
                    if success:
                        logger.info(f"✅ Пакет {argos_src}->{argos_tgt} установлен")
                        installed_packages = argostranslate.package.get_installed_packages()
                        for package in installed_packages:
                            if package.from_code == argos_src and package.to_code == argos_tgt:
                                ru_package = package
                                break
                    else:
                        logger.warning("⚠️ install_package_for_language_pair вернул False, пробуем fallback...")
                        argostranslate.package.update_package_index()
                        available_packages = argostranslate.package.get_available_packages()
                        for package in available_packages:
                            if package.from_code == argos_src and package.to_code == argos_tgt:
                                try:
                                    download_path = package.download()
                                    if download_path:
                                        argostranslate.package.install_from_path(download_path)
                                        ru_package = package
                                        logger.info(f"✅ Пакет {package.from_code}->{package.to_code} установлен через download")
                                    break
                                except Exception as dl_err:
                                    logger.error(f"❌ Ошибка загрузки пакета: {dl_err}")
                                    break
                except Exception as install_err:
                    logger.error(f"❌ Ошибка установки пакета: {install_err}")
            
            if not ru_package:
                logger.error(f"❌ Не удалось установить пакет перевода {argos_src}->{argos_tgt}")
                self._available = False
                return False
            
            self._model = argostranslate.translate
            
            # ✅ ИСПРАВЛЕНО V3: Тестовый перевод для проверки работоспособности
            # Проверяем, что Argos действительно может перевести (включая Stanza SBD)
            logger.info("🧪 Тестовый перевод для проверки Argos...")
            try:
                test_result = self._model.translate("Hello world", argos_src, argos_tgt)
                if test_result and test_result.strip() and test_result != "Hello world":
                    logger.info(f"✅ Argos Translate готов к работе (тест: '{test_result}')")
                    self._available = True
                    return True
                else:
                    logger.warning(f"⚠️ Тестовый перевод вернул оригинал: '{test_result}'")
                    self._available = False
                    return False
            except Exception as test_err:
                logger.error(f"❌ Тестовый перевод провалился: {test_err}")
                self._available = False
                self._init_error = str(test_err)
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Argos: {e}")
            self._available = False
            self._init_error = str(e)
            return False
    
    def is_available(self) -> bool:
        """Проверяет доступность движка (с ленивой инициализацией)"""
        if self._available is None:
            self.initialize()
        return self._available == True
    
    def get_name(self) -> str:
        """Возвращает имя движка"""
        return self.name
    
    def translate(self, text: str) -> Optional[str]:
        """
        Переводит текст через Argos Translate.
        Защищает и восстанавливает плейсхолдеры.
        """
        if not self.is_available():
            logger.warning("Argos недоступен")
            return None
        
        if not text or text.strip() == "":
            return text
        
        try:
            argos_src = self._get_argos_lang_code(self.src_lang)
            argos_tgt = self._get_argos_lang_code(self.tgt_lang)
            
            # ✅ Защита плейсхолдеров ПЕРЕД переводом
            protected_text = self._protect_placeholders(text)
            
            translated = self._model.translate(protected_text, argos_src, argos_tgt)
            
            # ✅ Проверка: убеждаемся что это строка
            if isinstance(translated, tuple):
                logger.warning(f"⚠️ Argos вернул кортеж вместо строки!")
                translated = translated[0] if translated else text
            
            if not translated or str(translated).strip() == "":
                logger.warning(f"⚠️ Пустой перевод для: {text[:50]}...")
                return None
            
            if translated == text:
                logger.debug(f"⚠️ Перевод равен оригиналу: {text[:50]}...")
            
            # ✅ Восстановление плейсхолдеров ПОСЛЕ перевода
            translated = self._restore_placeholders(str(translated))
            
            logger.debug(f"✅ Переведено: {text[:30]}... → {str(translated)[:30]}...")
            return str(translated)
            
        except Exception as e:
            logger.error(f"❌ Ошибка перевода: {e}")
            return None
