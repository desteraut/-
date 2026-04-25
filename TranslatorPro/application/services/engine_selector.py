"""
application/services/engine_selector.py
Селектор движков с fallback policy
ИСПРАВЛЕНО: Public методы EngineManager
"""
from typing import Optional, List
import logging
from ports.translation_port import TranslationPort
from infrastructure.engines.engine_manager import EngineManager

logger = logging.getLogger(__name__)

class EngineSelector:
    """Селектор движков с fallback policy"""
    
    def __init__(self, engine_manager: EngineManager):
        self._engine_manager = engine_manager
        self._usage_stats = {}
    
    def select_engine(self, preferred: Optional[str] = None) -> Optional[TranslationPort]:
        """Выбирает движок для перевода"""
        if preferred:
            engine = self._engine_manager.get_engine_by_name(preferred)
            if engine and self._engine_manager.check_engine_health(preferred):
                self._track_usage(preferred)
                logger.info(f"🎯 Selected preferred engine: {preferred}")
                return engine
        
        engine = self._engine_manager.get_primary_engine()
        if engine:
            self._track_usage(engine.name)
            logger.info(f"🎯 Selected primary engine: {engine.name}")
            return engine
        
        logger.warning("⚠️ No engines available")
        return None
    
    def translate_with_fallback(
        self,
        text: str,
        preferred_engine: Optional[str] = None,
        max_retries: int = 2
    ) -> Optional[str]:
        """Переводит текст с автоматическим fallback"""
        attempted_engines = []
        last_error = None
        
        for attempt in range(max_retries + 1):
            if attempt == 0:
                engine = self._engine_manager.get_engine_by_name(preferred_engine) if preferred_engine else self._engine_manager.get_primary_engine()
            else:
                primary_name = attempted_engines[-1] if attempted_engines else None
                engine = self._engine_manager.get_fallback_engine(primary_name) if primary_name else self._engine_manager.get_primary_engine()
            
            if not engine:
                logger.warning(f"⚠️ No more engines available (attempt {attempt + 1})")
                break
            
            if engine.name in attempted_engines:
                continue
            
            attempted_engines.append(engine.name)
            
            try:
                logger.debug(f"🔄 Translating with {engine.name} (attempt {attempt + 1})")
                result = engine.translate(text)
                
                if result and result.strip():
                    self._track_usage(engine.name)
                    logger.info(f"✅ Translation successful with {engine.name}")
                    return result
                else:
                    logger.warning(f"⚠️ Engine {engine.name} returned empty result")
                    
            except Exception as e:
                last_error = e
                logger.exception(f"❌ Engine {engine.name} failed: {e}")
        
        logger.error(f"❌ All engines failed. Attempted: {attempted_engines}")
        return None
    
    def _track_usage(self, engine_name: str) -> None:
        """Отслеживает статистику использования движков"""
        if engine_name not in self._usage_stats:
            self._usage_stats[engine_name] = {'count': 0, 'last_used': None}
        
        from datetime import datetime
        self._usage_stats[engine_name]['count'] += 1
        self._usage_stats[engine_name]['last_used'] = datetime.now()
    
    def get_usage_stats(self) -> dict:
        """Возвращает статистику использования движков"""
        return self._usage_stats.copy()