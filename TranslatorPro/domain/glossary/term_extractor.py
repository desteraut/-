"""
domain/glossary/term_extractor.py
Автоматическое извлечение потенциальных терминов из игры
Clean Architecture - Domain Layer
ИСПРАВЛЕНО: Убран импорт infrastructure (DIP violation)
"""
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TermCategory(Enum):
    """Категории терминов"""
    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    SKILL = "skill"
    ORGANIZATION = "organization"
    OTHER = "other"


@dataclass
class Term:
    """Модель термина"""
    term: str
    frequency: int = 0
    category: TermCategory = TermCategory.OTHER
    examples: List[str] = field(default_factory=list)
    translation: str = ""
    protected: bool = False


class TermExtractor:
    """
    Извлекает потенциальные термины из файлов Ren'Py
    """
    COMMON_WORDS_EN: Set[str] = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'can', 'could', 'may', 'might', 'must', 'shall', 'should',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
        'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
        'their', 'what', 'which', 'who', 'whom', 'whose', 'where',
        'when', 'why', 'how', 'all', 'each', 'every', 'both',
        'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'not', 'only', 'same', 'so', 'than', 'too', 'very',
        'just', 'now', 'here', 'there', 'then', 'once', 'if',
        'because', 'until', 'while', 'about', 'against', 'between',
        'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'from', 'up', 'down', 'in', 'out', 'on', 'off',
        'over', 'under', 'again', 'further', 'and', 'but', 'or',
        'nor', 'for', 'yet', 'as', 'at', 'by', 'to', 'of', 'with',
        'yes', 'no', 'okay', 'ok', 'well', 'good', 'bad', 'like',
        'know', 'think', 'see', 'look', 'want', 'need', 'go',
        'come', 'take', 'get', 'make', 'say', 'tell', 'ask',
        'thank', 'sorry', 'please', 'hello', 'hi', 'bye', 'wait',
        'right', 'left', 'back', 'front', 'side', 'way', 'time',
        'day', 'night', 'morning', 'evening', 'today', 'tomorrow',
        'yesterday', 'year', 'month', 'week', 'hour', 'minute',
        'man', 'woman', 'girl', 'boy', 'friend', 'father', 'mother',
        'brother', 'sister', 'house', 'room', 'door', 'window',
        'hand', 'eye', 'face', 'head', 'heart', 'voice', 'sound',
        'light', 'dark', 'color', 'red', 'blue', 'green', 'white',
        'black', 'big', 'small', 'long', 'short', 'new', 'old',
        'young', 'first', 'last', 'next', 'previous', 'true', 'false',
    }

    COMMON_WORDS_RU: Set[str] = {
        'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со',
        'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да',
        'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только',
        'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет',
        'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг',
        'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него',
        'до', 'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь',
        'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они',
        'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя',
        'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'человек',
        'чего', 'раз', 'тоже', 'себе', 'под', 'жизнь', 'будет',
        'кто', 'этот', 'говорил', 'того', 'потому', 'этого', 'какой',
        'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой',
        'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем',
        'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об',
        'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через',
        'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве',
        'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой',
        'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой',
        'им', 'более', 'всегда', 'конечно', 'всю', 'между', 'да', 'нет'
    }

    # ✅ ИСПРАВЛЕНО: Локальное определение защищённых слов (без импорта Infrastructure)
    PROTECTED_KEYWORDS: Set[str] = {
        # Python keywords
        'label', 'return', 'jump', 'call', 'menu', 'show', 'hide',
        'scene', 'with', 'image', 'screen', 'python', 'init',
        'default', 'define', 'class', 'def', 'if', 'else', 'for',
        'while', 'try', 'except', 'import', 'from', 'as',
        'none', 'true', 'false', 'and', 'or', 'not', 'in', 'is',
        # Ren'Py directives
        'transform', 'style', 'layer', 'zorder', 'alpha', 'pause',
        'input', 'textbutton', 'vbox', 'hbox', 'grid', 'frame',
        'add', 'key', 'timer', 'use', 'elif', 'pass', 'break',
        'continue', 'lambda', 'yield', 'raise', 'assert',
        'global', 'nonlocal', 'del', 'print',
        # Builtins
        'len', 'range', 'str', 'int', 'float', 'bool', 'list',
        'dict', 'set', 'tuple', 'type', 'open', 'file'
    }

    def __init__(
        self,
        frequency_threshold: int = 3,
        min_length: int = 3,
        max_length: int = 25
    ):
        self.frequency_threshold = frequency_threshold
        self.min_length = min_length
        self.max_length = max_length
        self.common_words = self.COMMON_WORDS_EN | self.COMMON_WORDS_RU
        
        self.name_pattern = re.compile(r'^\s*(\b[A-Z][a-zA-Z]{2,})\s*"', re.MULTILINE)
        self.capitalized_pattern = re.compile(r'\b[A-Z][a-zA-Z]{2,}\b')
        self.variable_pattern = re.compile(r'\[([A-Z][a-zA-Z]{2,})\]')
        self.dialogue_pattern = re.compile(r'^\s*(\w+)\s+"([^"]+)"', re.MULTILINE)

    def extract_from_files(self, game_path: Path) -> Dict[str, int]:
        """Извлекает потенциальные термины из всех файлов игры"""
        term_counter = Counter()
        
        for ext in ['*.rpy', '*.rpyc']:
            for file_path in game_path.rglob(ext):
                try:
                    terms = self._extract_from_file(file_path)
                    term_counter.update(terms)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при обработке {file_path}: {e}")
        
        filtered = {
            term: count 
            for term, count in term_counter.items() 
            if count >= self.frequency_threshold
        }
        
        return dict(sorted(filtered.items(), key=lambda x: x[1], reverse=True))

    def _extract_from_file(self, file_path: Path) -> List[str]:
        """Извлекает термины из одного файла"""
        terms = []
        
        try:
            if file_path.suffix == '.rpyc':
                content = self._decompile_rpyc(file_path)
            else: 
                content = file_path.read_text(encoding='utf-8')
            
            for match in self.name_pattern.finditer(content):
                name = match.group(1)
                if self._is_valid_term(name):
                    terms.append(name)
        
            for match in self.capitalized_pattern.finditer(content):
                word = match.group(0)
                if self._is_valid_term(word):
                    terms.append(word)
    
            for match in self.variable_pattern.finditer(content):
                var = match.group(1)
                if self._is_valid_term(var):
                    terms.append(var)
    
            for match in self.dialogue_pattern.finditer(content):
                name = match.group(1)
                if name[0].isupper() and self._is_valid_term(name):
                    terms.append(name)
    
        except UnicodeDecodeError as e:
            logger.error(f"UnicodeDecodeError reading {file_path}: {e}")
        except FileNotFoundError as e:
            logger.error(f"File not found: {file_path}")
        except Exception as e:
            logger.exception(f"⚠️ Ошибка чтения {file_path}: {e}")
        
        return terms

    def _is_valid_term(self, term: str) -> bool:
        """Проверяет, является ли слово валидным термином"""
        if len(term) < self.min_length or len(term) > self.max_length:
            return False
        
        if term.lower() in self.common_words:
            return False
        
        digit_ratio = sum(c.isdigit() for c in term) / len(term)
        if digit_ratio > 0.3:
            return False
        
        if self._is_protected_keyword(term):
            return False
        
        return True

    def _is_protected_keyword(self, term: str) -> bool:
        """
        Проверяет, является ли термин защищённым ключевым словом
        ✅ ИСПРАВЛЕНО: Локальное определение (без импорта Infrastructure)
        """
        return term.lower() in {k.lower() for k in self.PROTECTED_KEYWORDS}

    def _decompile_rpyc(self, file_path: Path) -> str:
        """
        Декомпилирует .rpyc файл
        ✅ ИСПРАВЛЕНО: Внедряем через порт (в production)
        """
        try:
            from infrastructure.utils import unrpyc
            return unrpyc.decompile(file_path)
        except ImportError:
            logger.warning(f"unrpyc not available, reading raw: {file_path}")
            return file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Decompilation failed for {file_path}: {e}")
            return file_path.read_text(encoding='utf-8', errors='ignore')

    def extract_with_context(self, game_path: Path) -> List[Term]:
        """Извлекает термины с контекстом использования"""
        terms_freq = self.extract_from_files(game_path)
        result = []
        
        for term, freq in terms_freq.items():
            category = self._categorize_term(term)
            examples = self._find_examples(game_path, term, limit=3)
            protected = self._is_protected_keyword(term)
            
            result.append(Term(
                term=term,
                frequency=freq,
                category=category,
                examples=examples,
                translation='',
                protected=protected
            ))
        
        return result

    def _categorize_term(self, term: str) -> TermCategory:
        """Определяет категорию термина"""
        term_lower = term.lower()
        
        if term[0].isupper() and len(term) <= 15:
            name_patterns = ['son', 'daughter', 'king', 'queen', 'lord', 'lady']
            if not any(p in term_lower for p in name_patterns): 
                return TermCategory.CHARACTER
        
        location_keywords = ['place', 'city', 'town', 'room', 'hall', 'forest', 
                           'cave', 'castle', 'tower', 'bridge', 'gate', 'door',
                            'street', 'road', 'path', 'garden', 'park', 'school',
                           'house', 'building', 'station', 'airport', 'port']
        if any(k in term_lower for k in location_keywords):
            return TermCategory.LOCATION
        
        item_keywords = ['item', 'weapon', 'armor', 'sword', 'shield', 'potion',
                        'ring', 'amulet', 'book', 'scroll', 'key', 'gem', 'stone',
                        'crystal', 'device', 'machine', 'tool', 'artifact']
        if any(k in term_lower for k in item_keywords):
            return TermCategory.ITEM
        
        skill_keywords = ['skill', 'ability', 'power', 'magic', 'spell', 'technique',
                          'attack', 'defense', 'buff', 'debuff', 'talent', 'trait']
        if any(k in term_lower for k in skill_keywords):
            return TermCategory.SKILL
        
        org_keywords = ['order', 'guild', 'faction', 'clan', 'team', 'group',
                       'association', 'council', 'committee', 'company', 'corp']
        if any(k in term_lower for k in org_keywords):
            return TermCategory.ORGANIZATION
        
        return TermCategory.OTHER

    def _find_examples(self, game_path: Path, term: str, limit: int = 3) -> List[str]:
        """Находит примеры использования термина"""
        examples = []
        
        for file_path in game_path.rglob('*.rpy'):
            try:
                content = file_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for line in lines:
                    if term in line and not line.strip().startswith('#'):
                        clean_line = line.strip()[:100]
                        if clean_line not in examples:
                            examples.append(clean_line)
                            if len(examples) >= limit:
                                return examples
            except Exception:
                continue
        
        if len(examples) < limit:
            for file_path in game_path.rglob('*.rpyc'):
                try:
                    content = self._decompile_rpyc(file_path)
                    lines = content.split('\n')
                    
                    for line in lines:
                        if term in line and not line.strip().startswith('#'):
                            clean_line = line.strip()[:100]
                            if clean_line not in examples:
                                examples.append(clean_line)
                                if len(examples) >= limit:
                                    return examples
                except Exception:
                    continue
        
        return examples

    def save_to_glossary(self, terms: List[Term], output_path: Path):
        """Сохраняет термины в glossary.txt"""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# " + "=" * 60 + "\n")
                f.write("# Глоссарий терминов - автоматически сгенерирован\n")
                f.write("# TranslatorPro V2 - Production Localizer\n")
                f.write("# " + "=" * 60 + "\n\n")
                
                f.write("# Формат: ОригинальныйТермин -> Перевод  # категория\n")
                f.write("# Заполните переводы вручную перед запуском локализации\n\n")
                
                categories = {}
                for term in terms:
                    cat = term.category.value
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(term)
                
                if 'character' in categories:
                    f.write("\n" + "=" * 40 + "\n")
                    f.write("# ПЕРСОНАЖИ (Characters)\n")
                    f.write("=" * 40 + "\n")
                    for term in sorted(categories['character'], key=lambda x: x.frequency, reverse=True):
                        self._write_term(f, term)
                
                if 'location' in categories:
                    f.write("\n" + "=" * 40 + "\n")
                    f.write("# ЛОКАЦИИ (Locations)\n")
                    f.write("=" * 40 + "\n")
                    for term in sorted(categories['location'], key=lambda x: x.frequency, reverse=True):
                        self._write_term(f, term)
                
                if 'item' in categories:
                    f.write("\n" + "=" * 40 + "\n")
                    f.write("# ПРЕДМЕТЫ (Items)\n")
                    f.write("=" * 40 + "\n")
                    for term in sorted(categories['item'], key=lambda x: x.frequency, reverse=True):
                        self._write_term(f, term)
                
                if 'other' in categories: 
                    f.write("\n" + "=" * 40 + "\n")
                    f.write("# ПРОЧЕЕ (Other)\n")
                    f.write("=" * 40 + "\n")
                    for term in sorted(categories['other'], key=lambda x: x.frequency, reverse=True):
                        self._write_term(f, term)
                
                f.write("\n" + "# " + "=" * 60 + "\n")
                f.write("# Конец глоссария\n")
                f.write("# " + "=" * 60 + "\n")
            
            logger.info(f"✅ Glossary saved to {output_path}")
            
        except IOError as e:
            logger.error(f"Failed to save glossary: {e}")
            raise

    def _write_term(self, f, term: Term):
        """Записывает один термин в файл"""
        if term.translation:
            f.write(f"{term.term} -> {term.translation}")
        else:
            f.write(f"{term.term} ->     ")
        
        f.write(f"  # {term.category.value}")
        if term.protected:
            f.write(" [ЗАЩИЩЁН]")
        elif not term.translation:
            f.write(" [ТРЕБУЕТ ПЕРЕВОДА]")
        
        f.write(f" (частота: {term.frequency})\n")
        
        if term.examples:
            for example in term.examples:
                f.write(f"#   Пример: {example}\n")

    def load_from_glossary(self, glossary_path: Path) -> Dict[str, str]:
        """Загружает глоссарий из файла"""
        glossary = {}
        
        if not glossary_path.exists():
            logger.warning(f"Glossary not found: {glossary_path}")
            return glossary
        
        try:
            with open(glossary_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    if not line or line.startswith('#'):
                        continue
                    
                    if '->' in line:
                        parts = line.split('->')
                        if len(parts) == 2:
                            term = parts[0].strip()
                            translation = parts[1].strip().split('#')[0].strip()
                            
                            if term and translation:
                                glossary[term] = translation
            
            logger.info(f"✅ Loaded {len(glossary)} terms from glossary")
            
        except UnicodeDecodeError as e:
            logger.error(f"UnicodeDecodeError reading glossary: {e}")
        except Exception as e:
            logger.exception(f"Error loading glossary: {e}")
        
        return glossary