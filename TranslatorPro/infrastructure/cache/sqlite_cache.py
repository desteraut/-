"""
infrastructure/cache/sqlite_cache.py
SQLite-кэш с версионированием и metadata
ИСПРАВЛЕНО: Versioned cache keys, QA-флаг, metadata для инвалидации
Согласно PDF "Решение ключевых проблем локализации в Ren'Py"
"""
import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager

# ✅ ИСПРАВЛЕНО: __name__ вместо name
logger = logging.getLogger(__name__)


class SQLiteCache:
    """
    SQLite-кэш с версионированием
    """
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS translation_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key TEXT UNIQUE NOT NULL,
        original_text TEXT NOT NULL,
        translated_text TEXT NOT NULL,
        source_lang TEXT NOT NULL,
        target_lang TEXT NOT NULL,
        file_path TEXT,
        line_number INTEGER,
        speaker TEXT,
        item_type TEXT,
        engine_name TEXT NOT NULL,
        engine_model_version TEXT,
        glossary_version TEXT,
        qa_passed INTEGER DEFAULT 1,
        qa_issues TEXT,
        placeholders_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        use_count INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS cache_metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_cache_key ON translation_cache(cache_key);
    CREATE INDEX IF NOT EXISTS idx_lookup ON translation_cache(source_lang, target_lang, original_text);
    CREATE INDEX IF NOT EXISTS idx_file ON translation_cache(file_path);
    """

    def __init__(self, db_path: Path, wal_mode: bool = True):
        self.db_path = db_path.resolve()
        self.wal_mode = wal_mode
        self._init_db()
        logger.info(f"✅ SQLite cache initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для подключений с транзакциями"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.exception(f"Transaction failed: {e}")
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Инициализирует базу данных"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._get_connection() as conn:
                if self.wal_mode:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute("PRAGMA cache_size=10000")
                
                conn.executescript(self.SCHEMA)
                
                # Миграция: добавляем speaker/item_type если их нет
                try:
                    conn.execute("ALTER TABLE translation_cache ADD COLUMN speaker TEXT")
                    logger.info("Миграция: добавлена колонка speaker")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
                try:
                    conn.execute("ALTER TABLE translation_cache ADD COLUMN item_type TEXT")
                    logger.info("Миграция: добавлена колонка item_type")
                except sqlite3.OperationalError:
                    pass  # Колонка уже существует
                
                logger.debug("Database schema initialized")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _generate_cache_key(
        self,
        original_text: str,
        source_lang: str,
        target_lang: str,
        glossary_version: str,
        engine_model_version: str
    ) -> str:
        """Генерирует детерминированный ключ кэша с учётом версий"""
        key_data = f"{original_text}|{source_lang}|{target_lang}|{glossary_version}|{engine_model_version}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()

    def get_translation(
        self,
        original: str,
        src_lang: str,
        tgt_lang: str,
        file_path: str,
        line_number: int,
        glossary_version: str = "",
        engine_model_version: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Получение перевода из кэша с проверкой версий"""
        cache_key = self._generate_cache_key(
            original, src_lang, tgt_lang, glossary_version, engine_model_version
        )
        
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT translated_text, engine_name, engine_model_version, 
                           glossary_version, qa_passed, qa_issues, placeholders_json,
                           use_count, last_used_at
                    FROM translation_cache
                    WHERE cache_key = ?
                    """,
                    (cache_key,)
                )
                row = cursor.fetchone()
                
                if row:
                    conn.execute(
                        "UPDATE translation_cache SET use_count = use_count + 1, last_used_at = CURRENT_TIMESTAMP WHERE cache_key = ?",
                        (cache_key,)
                    )
                    
                    logger.debug(f"✅ Cache HIT: {original[:50]}...")
                    return {
                        'translated_text': row['translated_text'],
                        'engine_name': row['engine_name'],
                        'engine_model_version': row['engine_model_version'],
                        'glossary_version': row['glossary_version'],
                        'qa_passed': bool(row['qa_passed']),
                        'qa_issues': json.loads(row['qa_issues']) if row['qa_issues'] else None,
                        'placeholders': json.loads(row['placeholders_json']) if row['placeholders_json'] else {},
                        'cache_hit': True,
                        'use_count': row['use_count']
                    }
                else:
                    logger.debug(f"❌ Cache MISS: {original[:50]}...")
                    return None
                
        except sqlite3.Error as e:
            logger.error(f"Cache get failed: {e}")
            return None

    def save_translation(
        self,
        original: str,
        translated: str,
        src_lang: str,
        tgt_lang: str,
        file_path: str,
        line_number: int,
        engine_name: str,
        glossary_version: str = "",
        engine_model_version: str = "",
        speaker: Optional[str] = None,
        item_type: Optional[str] = None,
        placeholders: Optional[Dict[str, str]] = None,
        qa_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Сохранение перевода в кэш с metadata"""
        cache_key = self._generate_cache_key(
            original, src_lang, tgt_lang, glossary_version, engine_model_version
        )
        
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO translation_cache 
                    (cache_key, original_text, translated_text, source_lang, target_lang,
                     file_path, line_number, speaker, item_type, engine_name, engine_model_version, 
                     glossary_version, qa_passed, qa_issues, placeholders_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cache_key,
                        original,
                        translated,
                        src_lang,
                        tgt_lang,
                        file_path,
                        line_number,
                        speaker,
                        item_type,
                        engine_name,
                        engine_model_version,
                        glossary_version,
                        1 if (qa_result and qa_result.get('valid', True)) else 0,
                        json.dumps(qa_result.get('issues', [])) if qa_result else None,
                        json.dumps(placeholders) if placeholders else None
                    )
                )
                
                logger.debug(f"✅ Cache SAVE: {original[:50]}...")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Cache save failed: {e}")
            return False

    def invalidate_by_glossary(self, glossary_version: str) -> int:
        """Массовая инвалидация кэша при обновлении глоссария"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM translation_cache WHERE glossary_version != ?",
                    (glossary_version,)
                )
                count = cursor.fetchone()[0]
                
                conn.execute(
                    "DELETE FROM translation_cache WHERE glossary_version != ?",
                    (glossary_version,)
                )
                
                logger.info(f"🗑️ Invalidated {count} cache entries (glossary_version={glossary_version})")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0

    def invalidate_by_engine(self, engine_name: str, model_version: str) -> int:
        """Массовая инвалидация кэша при обновлении модели движка"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM translation_cache WHERE engine_name = ? AND engine_model_version != ?",
                    (engine_name, model_version)
                )
                count = cursor.fetchone()[0]
                
                conn.execute(
                    "DELETE FROM translation_cache WHERE engine_name = ? AND engine_model_version != ?",
                    (engine_name, model_version)
                )
                
                logger.info(f"🗑️ Invalidated {count} cache entries (engine={engine_name}, version={model_version})")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Cache invalidation failed: {e}")
            return 0

    def clear_cache(self, older_than_days: Optional[int] = None) -> int:
        """Очистка кэша"""
        try:
            with self._get_connection() as conn:
                if older_than_days:
                    cutoff = datetime.now() - timedelta(days=older_than_days)
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM translation_cache WHERE last_used_at < ?",
                        (cutoff.isoformat(),)
                    )
                    count = cursor.fetchone()[0]
                    
                    conn.execute(
                        "DELETE FROM translation_cache WHERE last_used_at < ?",
                        (cutoff.isoformat(),)
                    )
                else:
                    cursor = conn.execute("SELECT COUNT(*) FROM translation_cache")
                    count = cursor.fetchone()[0]
                    conn.execute("DELETE FROM translation_cache")
                
                logger.info(f"🗑️ Cleared {count} cache entries")
                return count
                
        except sqlite3.Error as e:
            logger.error(f"Cache clear failed: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        try:
            with self._get_connection() as conn:
                total = conn.execute("SELECT COUNT(*) FROM translation_cache").fetchone()[0]
                qa_passed = conn.execute(
                    "SELECT COUNT(*) FROM translation_cache WHERE qa_passed = 1"
                ).fetchone()[0]
                total_uses = conn.execute(
                    "SELECT SUM(use_count) FROM translation_cache"
                ).fetchone()[0] or 0
                
                return {
                    'total_entries': total,
                    'qa_passed_entries': qa_passed,
                    'qa_failed_entries': total - qa_passed,
                    'total_uses': total_uses,
                    'hit_rate': f"{(qa_passed / total * 100) if total > 0 else 0:.1f}%"
                }
                
        except sqlite3.Error as e:
            logger.error(f"Cache stats failed: {e}")
            return {'error': str(e)}

    def set_metadata(self, key: str, value: str) -> bool:
        """Сохраняет метаданные"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache_metadata (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (key, value)
                )
                return True
        except sqlite3.Error as e:
            logger.error(f"Metadata save failed: {e}")
            return False

    def get_metadata(self, key: str) -> Optional[str]:
        """Получает метаданные по ключу"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT value FROM cache_metadata WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row['value'] if row else None
        except sqlite3.Error as e:
            logger.error(f"Metadata get failed: {e}")
            return None

    def get_all_translations(self, tgt_lang: str = "russian") -> List[Dict[str, Any]]:
        """Получает все переводы для генерации языкового пакета"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT original_text, translated_text, file_path, line_number,
                           engine_name, qa_passed, speaker, item_type
                    FROM translation_cache
                    WHERE target_lang = ?
                    """,
                    (tgt_lang,)
                )
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'text': row['original_text'],
                        'translated': row['translated_text'],
                        'original_text': row['original_text'],
                        'translated_text': row['translated_text'],
                        'file': row['file_path'],
                        'file_path': row['file_path'],
                        'line': row['line_number'],
                        'line_number': row['line_number'],
                        'speaker': row['speaker'],
                        'type': row['item_type'] or 'dialogue',
                        'engine_name': row['engine_name'],
                        'qa_passed': bool(row['qa_passed'])
                    })
                
                logger.info(f"📊 Получено {len(results)} переводов для {tgt_lang}")
                return results
                
        except sqlite3.Error as e:
            logger.error(f"Get all translations failed: {e}")
            return []