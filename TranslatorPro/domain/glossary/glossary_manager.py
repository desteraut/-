"""
GlossaryManager — менеджер глоссария с поддержкой авто-извлечения
СТАРАЯ РАБОЧАЯ ВЕРСИЯ — возвращает СТРОКУ, а не кортеж!
Архитектура: Clean Architecture (Domain Layer)
"""
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from .term_extractor import TermExtractor
import logging

# ✅ ИСПРАВЛЕНО: __name__ вместо name
logger = logging.getLogger(__name__)


class GlossaryManager:
    """Управление глоссарием терминов"""
    
    def __init__(self, glossary_path: Optional[Path] = None):
        self.glossary_path = glossary_path or Path('glossary.txt')
        self.terms: Dict[str, str] = {}
        self.placeholders: Dict[str, str] = {}
        self.extractor = TermExtractor()
        self.extracted_terms: List = []
        self._load()

    def _load(self):
        """Загружает глоссарий из файла"""
        if not self.glossary_path.exists():
            return
        
        try:
            with open(self.glossary_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '->' in line and not line.startswith('#'):
                        key, value = line.split('->', 1)
                        key = key.strip()
                        value = value.strip().split('#')[0].strip()
                        if key and value:
                            self.terms[key] = value
            
            logger.info(f"✅ Загружено {len(self.terms)} терминов из глоссария")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки глоссария: {e}")

    def save(self):
        """Сохраняет глоссарий в файл"""
        try:
            self.glossary_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.glossary_path, 'w', encoding='utf-8') as f:
                f.write("# " + "=" * 60 + "\n")
                f.write("# Глоссарий терминов - TranslatorPro V3\n")
                f.write("# " + "=" * 60 + "\n\n")
                f.write("# Формат: ОригинальныйТермин -> Перевод\n\n")
                
                for key, value in self.terms.items():
                    f.write(f"{key} -> {value}\n")
            
            logger.info(f"✅ Сохранено {len(self.terms)} терминов")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения глоссария: {e}")

    def add(self, term: str, translation: str):
        """Добавляет термин в глоссарий"""
        self.terms[term] = translation
        self.save()

    def remove(self, term: str):
        """Удаляет термин из глоссария"""
        if term in self.terms:
            del self.terms[term]
            self.save()

    def clear(self):
        """Очищает весь глоссарий"""
        self.terms.clear()
        self.placeholders.clear()
        self.save()

    def get_terms_count(self) -> int:
        """Возвращает количество терминов"""
        return len(self.terms)

    def apply(self, text: str, direction: str = "pre") -> str:
        """
        Применяет глоссарий к тексту
        
        ✅ ВАЖНО: Возвращает СТРОКУ, а не кортеж!
        direction: "pre" (до перевода) или "post" (после перевода)
        """
        # Сортировка по длине для корректной замены
        sorted_terms = sorted(self.terms.items(), key=lambda x: len(x[0]), reverse=True)
        
        if direction == "pre":
            # Заменяем термины на плейсхолдеры ПЕРЕД переводом
            for key, value in sorted_terms:
                term_hash = hashlib.md5(key.encode()).hexdigest()[:8]
                placeholder = f"###TERM_{term_hash}###"
                self.placeholders[placeholder] = value
                # ✅ Исправлено: (?<!\w) и (?!\w) вместо \b для кириллицы
                pattern = r'(?<!\w)' + re.escape(key) + r'(?!\w)'
                text = re.sub(pattern, placeholder, text, flags=re.IGNORECASE)
        else:
            # Восстанавливаем термины ПОСЛЕ перевода
            for placeholder, term_value in self.placeholders.items():
                text = text.replace(placeholder, term_value)
        
        return text  # ✅ Возвращаем СТРОКУ

    def auto_extract(self, game_path: Path) -> List:
        """Авто-извлечение терминов из игры"""
        try:
            self.extracted_terms = self.extractor.extract_with_context(game_path)
            logger.info(f"✅ Извлечено {len(self.extracted_terms)} потенциальных терминов")
            return self.extracted_terms
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения терминов: {e}")
            return []

    def review_and_save(self, terms: List, output_path: Optional[Path] = None):
        """Сохраняет извлечённые термины"""
        path = output_path or self.glossary_path
        self.extractor.save_to_glossary(terms, path)
        
        # Добавляем переведённые термины в активный глоссарий
        for term_data in terms:
            if hasattr(term_data, 'translation') and term_data.translation:
                self.terms[term_data.term] = term_data.translation
            elif isinstance(term_data, dict) and term_data.get('translation'):
                self.terms[term_data['term']] = term_data['translation']
        
        self.save()

    def get_all_terms(self) -> List[Dict]:
        """Возвращает все термины с метаданными"""
        return [
            {
                'term': term,
                'translation': translation,
                'frequency': '-',
                'category': 'loaded',
                'examples': []
            }
            for term, translation in self.terms.items()
        ]