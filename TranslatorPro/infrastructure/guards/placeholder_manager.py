"""
PlaceholderManager — Управление плейсхолдерами и метаданными
"""

import re
import json
import hashlib
from typing import Dict, Tuple, Optional, List
from pathlib import Path


class PlaceholderManager:
    """Управление информацией о плейсхолдерах"""
    
    def __init__(self):
        self.counter = 0
        self.placeholders_db: Dict[str, Tuple[str, Dict[str, str]]] = {}
        self.var_pattern = re.compile(r'§§VAR_[a-zA-Z0-9_]+§§')
        self.bracket_pattern = re.compile(r'\[([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\]')
    
    def generate_uid(self, base_string: str, placeholders_dict: Dict[str, str]) -> str:
        """Генерация уникального идентификатора"""
        content = f"{base_string}|{json.dumps(placeholders_dict, sort_keys=True)}"
        uid_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
        uid = f"PH_{self.counter}_{uid_hash}"
        self.counter += 1
        
        self.placeholders_db[uid] = (base_string, placeholders_dict.copy())
        
        return uid
    
    def get_original_structure(self, uid: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Получение оригинальной структуры по UID"""
        return self.placeholders_db.get(uid, None)
    
    def extract_placeholders_from_text(self, text: str) -> Dict[str, str]:
        """Извлекает все плейсхолдеры из текста"""
        placeholders = {}
        
        for match in self.var_pattern.finditer(text):
            var_id = match.group(0)
            placeholders[var_id] = var_id
        
        for match in self.bracket_pattern.finditer(text):
            var_name = match.group(1)
            var_full = match.group(0)
            placeholders[var_full] = var_name
        
        return placeholders
    
    def restore_placeholders(self, translated_text: str, placeholders_dict: Dict[str, str]) -> str:
        """Восстанавливает плейсхолдеры в переведённом тексте"""
        result = translated_text
        
        for var_id, var_name in placeholders_dict.items():
            if var_id.startswith('§§VAR_'):
                pattern = re.escape(var_id)
                replacement = f"[{var_name}]"
                result = re.sub(pattern, replacement, result)
            elif var_id.startswith('[') and var_id.endswith(']'):
                if var_id not in result:
                    logger_warning = f"Плейсхолдер {var_id} потерян при переводе!"
                    result = result.replace(var_name, var_id, 1) if var_name in result else result
        
        return result
    
    def validate_placeholder_count(self, original: str, translated: str) -> bool:
        """Проверяет соответствие количества плейсхолдеров"""
        orig_count = len(self.var_pattern.findall(original)) + len(self.bracket_pattern.findall(original))
        trans_count = len(self.var_pattern.findall(translated)) + len(self.bracket_pattern.findall(translated))
        
        return orig_count == trans_count
    
    def save_to_file(self, filepath: Path):
        """Сохраняет базу плейсхолдеров в файл"""
        data = {
            'counter': self.counter,
            'placeholders_db': {
                uid: list(value) for uid, value in self.placeholders_db.items()
            }
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: Path):
        """Загружает базу плейсхолдеров из файла"""
        if not filepath.exists():
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.counter = data.get('counter', 0)
        self.placeholders_db = {
            uid: tuple(value) for uid, value in data.get('placeholders_db', {}).items()
        }
    
    def clear(self):
        """Очищает базу плейсхолдеров"""
        self.counter = 0
        self.placeholders_db.clear()
    
    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику по плейсхолдерам"""
        return {
            'total_uids': len(self.placeholders_db),
            'counter': self.counter
        }