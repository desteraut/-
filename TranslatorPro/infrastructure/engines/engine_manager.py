"""
infrastructure/engines/engine_manager.py
Менеджер жизненного цикла движков перевода
ИСПРАВЛЕНО: Public методы для доступа из EngineSelector
"""
from typing import List, Dict, Optional
from pathlib import Path
import threading
import logging
from datetime import datetime, timedelta
from ports.translation_port import TranslationPort

logger = logging.getLogger(__name__)

class EngineHealthStatus:
    """Статус здоровья движка"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

class EngineManager:
    """
    Централизованное управление жизненным циклом движков перевода
    """
    
    def __init__(self, engines: List[TranslationPort], health_check_ttl: int = 300):
        self._engines = {engine.name: engine for engine in engines}
        self._health_cache: Dict[str, Dict] = {}
        self._health_ttl = timedelta(seconds=health_check_ttl)
        self._lock = threading.RLock()
        self._initialized = set()
        
        logger.info(f"✅ EngineManager initialized with {len(engines)} engines")
    
    def get_available_engines(self) -> List[str]:
        """Возвращает список доступных движков"""
        available = []
        with self._lock:
            for name, engine in self._engines.items():
                if self._check_health(name):
                    available.append(name)
        return available
    
    def get_primary_engine(self) -> Optional[TranslationPort]:
        """Возвращает первый доступный движок (приоритетный)"""
        with self._lock:
            for name in self._engines.keys():
                if self._check_health(name):
                    return self.get_engine_by_name(name)
        return None
    
    def get_fallback_engine(self, primary_name: str) -> Optional[TranslationPort]:
        """Возвращает резервный движок (следующий после primary)"""
        with self._lock:
            found_primary = False
            for name in self._engines.keys():
                if found_primary and self._check_health(name):
                    return self.get_engine_by_name(name)
                if name == primary_name:
                    found_primary = True
        return None
    
    # ✅ ИСПРАВЛЕНО: Public методы вместо private
    def get_engine_by_name(self, name: str) -> Optional[TranslationPort]:
        """Получает движок по имени с lazy-инициализацией"""
        engine = self._engines.get(name)
        if not engine:
            return None
        
        if name not in self._initialized:
            try:
                if hasattr(engine, 'initialize'):
                    engine.initialize()
                self._initialized.add(name)
                logger.info(f"✅ Engine '{name}' lazy-initialized")
            except Exception as e:
                logger.error(f"❌ Engine '{name}' initialization failed: {e}")
                self._health_cache[name] = {
                    'status': EngineHealthStatus.UNAVAILABLE,
                    'checked_at': datetime.now(),
                    'error': str(e)
                }
                return None
        
        return engine
    
    def check_engine_health(self, name: str) -> bool:
        """Проверяет здоровье движка с кэшированием"""
        return self._check_health(name)
    
    def _check_health(self, name: str) -> bool:
        """Внутренняя проверка здоровья"""
        now = datetime.now()
        
        if name in self._health_cache:
            cache = self._health_cache[name]
            if now - cache['checked_at'] < self._health_ttl:
                return cache['status'] == EngineHealthStatus.HEALTHY
        
        engine = self._engines.get(name)
        if not engine:
            self._health_cache[name] = {
                'status': EngineHealthStatus.UNAVAILABLE,
                'checked_at': now,
                'error': 'Engine not found'
            }
            return False
        
        try:
            is_available = engine.is_available()
            status = EngineHealthStatus.HEALTHY if is_available else EngineHealthStatus.UNAVAILABLE
            
            self._health_cache[name] = {
                'status': status,
                'checked_at': now,
                'error': None if is_available else 'is_available() returned False'
            }
            
            if is_available:
                logger.debug(f"✅ Engine '{name}' health check passed")
            else:
                logger.warning(f"⚠️ Engine '{name}' health check failed")
            
            return is_available
            
        except Exception as e:
            logger.exception(f"❌ Engine '{name}' health check exception: {e}")
            self._health_cache[name] = {
                'status': EngineHealthStatus.UNAVAILABLE,
                'checked_at': now,
                'error': str(e)
            }
            return False
    
    def health_check_all(self) -> Dict[str, str]:
        """Проверяет здоровье всех движков"""
        results = {}
        with self._lock:
            for name in self._engines.keys():
                self._check_health(name)
                results[name] = self._health_cache.get(name, {}).get('status', EngineHealthStatus.UNAVAILABLE)
        return results
    
    def shutdown(self) -> None:
        """Graceful shutdown: освобождение ресурсов"""
        logger.info("🔄 Shutting down EngineManager...")
        
        with self._lock:
            for name, engine in self._engines.items():
                try:
                    if hasattr(engine, 'shutdown'):
                        engine.shutdown()
                        logger.info(f"✅ Engine '{name}' shut down")
                    elif name in self._initialized:
                        logger.info(f"ℹ️ Engine '{name}' released (no shutdown method)")
                except Exception as e:
                    logger.error(f"❌ Error shutting down {name}: {e}")
            
            self._initialized.clear()
            self._health_cache.clear()
        
        logger.info("✅ EngineManager shutdown complete")
    
    def get_engine_stats(self) -> Dict[str, Dict]:
        """Возвращает статистику по движкам"""
        stats = {}
        with self._lock:
            for name, engine in self._engines.items():
                health = self._health_cache.get(name, {})
                stats[name] = {
                    'initialized': name in self._initialized,
                    'health_status': health.get('status', 'unknown'),
                    'last_check': health.get('checked_at', None),
                    'error': health.get('error')
                }
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        return False