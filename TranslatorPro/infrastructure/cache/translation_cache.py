"""
TranslationCache — SQLite кэш с расширенной структурой
"""

import sqlite3
import hashlib
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime


class TranslationCache:
    """SQLite кэш с поддержкой контекста и плейсхолдеров"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text_hash TEXT UNIQUE NOT NULL,
                    original_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    src_lang TEXT NOT NULL,
                    tgt_lang TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INTEGER,
                    speaker TEXT,
                    item_type TEXT,
                    placeholders_json TEXT,
                    context_json TEXT,
                    quality_score REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_text_hash ON translations(text_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON translations(file_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_languages ON translations(src_lang, tgt_lang)")
            
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            
            # Миграция: добавляем speaker/item_type если их нет
            try:
                conn.execute("ALTER TABLE translations ADD COLUMN speaker TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                conn.execute("ALTER TABLE translations ADD COLUMN item_type TEXT")
            except sqlite3.OperationalError:
                pass
            
            conn.commit()
    
    def _generate_hash(self, text: str, src_lang: str, tgt_lang: str,
                       file_path: str, line_number: int) -> str:
        """Генерация хэша с учётом контекста"""
        context_string = f"{text}|{src_lang}|{tgt_lang}|{file_path}|{line_number}"
        return hashlib.md5(context_string.encode('utf-8')).hexdigest()
    
    def save_translation(self, original: str, translated: str, src_lang: str,
                         tgt_lang: str, file_path: str, line_number: int,
                         speaker: Optional[str] = None,
                         item_type: Optional[str] = None,
                         placeholders: Optional[Dict[str, str]] = None,
                         context: Optional[Dict[str, Any]] = None,
                         quality_score: float = 0.0):
        """Сохранение перевода с метаданными"""
        text_hash = self._generate_hash(original, src_lang, tgt_lang,
                                        file_path, line_number)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO translations
                (text_hash, original_text, translated_text, src_lang, tgt_lang,
                 file_path, line_number, speaker, item_type, placeholders_json, context_json,
                 quality_score, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                text_hash,
                original,
                translated,
                src_lang,
                tgt_lang,
                file_path,
                line_number,
                speaker,
                item_type,
                json.dumps(placeholders, ensure_ascii=False) if placeholders else None,
                json.dumps(context, ensure_ascii=False) if context else None,
                quality_score
            ))
            conn.commit()
    
    def get_translation(self, original: str, src_lang: str, tgt_lang: str,
                        file_path: str, line_number: int) -> Optional[Dict[str, Any]]:
        """Получение перевода из кэша"""
        text_hash = self._generate_hash(original, src_lang, tgt_lang,
                                        file_path, line_number)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT translated_text, placeholders_json, context_json, quality_score
                FROM translations
                WHERE text_hash = ?
            """, (text_hash,))
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'translated_text': row['translated_text'],
                    'placeholders': json.loads(row['placeholders_json']) if row['placeholders_json'] else None,
                    'context': json.loads(row['context_json']) if row['context_json'] else None,
                    'quality_score': row['quality_score']
                }
        
        return None
    
    def cache_translation(self, original: str, translated: str,
                          file_path: str, line_number: int,
                          src_lang: str, tgt_lang: str,
                          speaker: Optional[str] = None,
                          item_type: Optional[str] = None):
        """Обратно-совместимый метод для сохранения перевода (вызывается из pipeline)."""
        self.save_translation(
            original=original,
            translated=translated,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            file_path=file_path,
            line_number=line_number,
            speaker=speaker,
            item_type=item_type
        )

    def get_all_translations(self, file_path: Optional[str] = None,
                             tgt_lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """Получение всех переводов с фильтрацией. Возвращает ключи, совместимые с renpy_generator."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM translations WHERE 1=1"
            params = []
            
            if file_path:
                query += " AND file_path = ?"
                params.append(file_path)
            
            if tgt_lang:
                query += " AND tgt_lang = ?"
                params.append(tgt_lang)
            
            query += " ORDER BY file_path, line_number"
            
            cursor = conn.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'text': row['original_text'],
                    'translated': row['translated_text'],
                    'original_text': row['original_text'],
                    'translated_text': row['translated_text'],
                    'file': row['file_path'],
                    'file_path': row['file_path'],
                    'line': row['line_number'],
                    'line_number': row['line_number'],
                    'src_lang': row['src_lang'],
                    'tgt_lang': row['tgt_lang'],
                    'speaker': row['speaker'],
                    'type': row['item_type'] or 'dialogue',
                    'placeholders': json.loads(row['placeholders_json']) if row['placeholders_json'] else None,
                    'quality_score': row['quality_score'],
                    'created_at': row['created_at']
                })
            
            return results
    
    def delete_translation(self, text_hash: str) -> bool:
        """Удаление перевода по хэшу"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM translations WHERE text_hash = ?", (text_hash,))
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_cache(self, older_than_days: Optional[int] = None):
        """Очистка кэша"""
        with sqlite3.connect(self.db_path) as conn:
            if older_than_days:
                conn.execute("DELETE FROM translations WHERE created_at < datetime('now', ?)",
                           (f'-{older_than_days} days',))
            else:
                conn.execute("DELETE FROM translations")
            conn.commit()
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as total, COUNT(DISTINCT file_path) as files,
                       AVG(quality_score) as avg_quality, MIN(created_at) as oldest,
                       MAX(created_at) as newest FROM translations
            """)
            
            row = cursor.fetchone()
            
            return {
                'total_translations': row[0],
                'unique_files': row[1],
                'average_quality': row[2] or 0.0,
                'oldest_entry': row[3],
                'newest_entry': row[4]
            }
    
    def export_to_json(self, output_path: Path):
        """Экспорт кэша в JSON файл"""
        translations = self.get_all_translations()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(translations, f, ensure_ascii=False, indent=2)
    
    def import_from_json(self, input_path: Path):
        """Импорт кэша из JSON файла"""
        with open(input_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        for t in translations:
            self.save_translation(
                original=t['original_text'],
                translated=t['translated_text'],
                src_lang=t['src_lang'],
                tgt_lang=t['tgt_lang'],
                file_path=t['file_path'],
                line_number=t['line_number'],
                placeholders=t.get('placeholders'),
                quality_score=t.get('quality_score', 0.0)
            )