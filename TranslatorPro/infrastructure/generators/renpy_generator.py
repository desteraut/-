"""
RenPyGenerator — генерация файлов перевода для Ren'Py 8.x
ИСПРАВЛЕНО V3:
  - Валидация перевода: проверка на кириллицу для русского языка
  - Более строгая фильтрация непереведённых строк
"""
import hashlib
import re
from typing import List, Dict, Optional, Set
from pathlib import Path
import logging

from infrastructure.utils.text_utils import is_file_path, escape_quotes_renpy

logger = logging.getLogger(__name__)


class RenPyGenerator:
    """Генератор файлов перевода для Ren'Py 8.x — правильный формат tl/"""

    def __init__(self, cache=None, code_dir: Optional[Path] = None,
                 language_code: str = "russian", language_name: str = "Русский"):
        self.cache = cache
        self.code_dir = code_dir
        self.language_code = language_code
        self.language_name = language_name
        self.language_folder = language_code
        self._cyrillic_pattern = re.compile(r'[\u0400-\u04FF\u0500-\u052F]')
        self._min_cyrillic_ratio = 0.15

    def _is_valid_translation(self, original: str, translated: str) -> bool:
        """Проверяет, действительно ли строка переведена."""
        if not original or not translated:
            return False
        if translated == original:
            return False
        # Для русского: должен содержать кириллицу
        if self.language_code.lower() in ("russian", "ru"):
            cyrillic_chars = len(self._cyrillic_pattern.findall(translated))
            total_chars = len(translated.strip())
            if total_chars > 0:
                ratio = cyrillic_chars / total_chars
                if ratio < self._min_cyrillic_ratio:
                    return False
        return True

    def _generate_block_id(self, text: str, line_number: int, speaker: str = "") -> str:
        """Генерирует уникальный идентификатор блока"""
        content = f"{speaker}:{text}:{line_number}"
        hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        return f"str_{hash_value}"

    def generate_language_pack(self, game_dir: Path, translations_data: Optional[List[Dict]] = None) -> Path:
        """
        Генерирует полный языковой пакет Ren'Py в game/tl/russian/

        Args:
            game_dir: Корневая папка игры (где лежит папка game/)
            translations_data: Список словарей с переводами (если не передан — берёт из кэша)
        """
        # Определяем правильный путь: если game_dir уже содержит game/, используем её,
        # иначе считаем что game_dir — это корень проекта и ищем game/ внутри
        if (game_dir / "game").exists() and (game_dir / "game").is_dir():
            output_dir = game_dir / "game" / "tl" / self.language_folder
        else:
            output_dir = game_dir / "tl" / self.language_folder
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Создаём language.rpy с регистрацией языка и шрифтами
        self._generate_language_rpy(output_dir)

        # 2. Получаем переводы
        if translations_data is None and self.cache:
            translations = self.cache.get_all_translations(tgt_lang=self.language_code)
        elif translations_data:
            translations = translations_data
        else:
            translations = []

        # Фильтруем файловые пути и НЕвалидные переводы
        filtered = [
            t for t in translations
            if not is_file_path(t.get('original_text', t.get('text', '')))
            and self._is_valid_translation(
                t.get('original_text', t.get('text', '')),
                t.get('translated', t.get('translated_text', ''))
            )
        ]

        logger.info(f"Валидных переводов для генерации: {len(filtered)} из {len(translations)}")

        # Разделяем на диалоги и строки интерфейса/меню
        dialogues = []
        strings = []
        menus = []

        for t in filtered:
            item_type = t.get('type', 'dialogue')
            if item_type == 'dialogue':
                dialogues.append(t)
            elif item_type == 'menu':
                menus.append(t)
            else:
                strings.append(t)

        # 3. Генерируем файлы перевода для каждого исходного скрипта (dialogue blocks)
        files_dict: Dict[str, List[Dict]] = {}
        for t in dialogues + menus:
            file_path = t.get('file', 'unknown')
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append(t)

        for orig_file, file_trans in files_dict.items():
            self._generate_translation_file(output_dir, orig_file, file_trans)

        # 4. Генерируем common.rpy для строк интерфейса (old/new формат)
        all_strings = strings + menus  # меню тоже идут в strings
        self._generate_common_rpy(output_dir, all_strings)

        # 5. Генерируем screens.rpy для экранов (если есть)
        self._generate_screens_rpy(output_dir, strings)

        logger.info(f"Языковой пакет создан: {output_dir}")
        return output_dir

    def _generate_language_rpy(self, output_dir: Path):
        """Создаёт language.rpy с регистрацией языка и шрифтами"""
        content = f'''# game/tl/{self.language_folder}/language.rpy
# Файл настройки языка для Ren'Py 8.x
# Ren'Py автоматически обнаруживает этот язык по папке tl/{self.language_folder}/

init -1 python:
    # Регистрация языка
    renpy.add_language("{self.language_code}", "{self.language_name}")

    # Шрифты для кириллицы (Noto Sans или DejaVu)
    gui.text_font = "fonts/DejaVuSans.ttf"
    gui.name_text_font = "fonts/DejaVuSans.ttf"
    gui.interface_text_font = "fonts/DejaVuSans.ttf"
    gui.button_text_font = "fonts/DejaVuSans.ttf"
    gui.choice_button_text_font = "fonts/DejaVuSans.ttf"
'''
        path = output_dir / "language.rpy"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Создан language.rpy: {path}")

    def _generate_translation_file(self, output_dir: Path, original_file: str,
                                    translations: List[Dict]):
        """
        Генерирует файл перевода с ПРАВИЛЬНЫМ форматом Ren'Py translate blocks:

        # game/file.rpy:line
        translate russian str_HASH:
            # speaker "Original text"
            speaker "Переведённый текст"
        """
        file_name = Path(original_file).name
        translation_file_path = output_dir / file_name

        # Убираем дубликаты по оригинальному тексту в рамках одного файла
        seen_texts: Set[str] = set()
        unique_trans = []
        for t in sorted(translations, key=lambda x: x.get('line', 0)):
            orig = t.get('text', t.get('original_text', ''))
            if orig not in seen_texts and not is_file_path(orig):
                seen_texts.add(orig)
                unique_trans.append(t)

        with open(translation_file_path, 'w', encoding='utf-8') as f:
            f.write(f"# Translation of {original_file}\n")
            f.write(f"# Generated by TranslatorPro V3\n")
            f.write(f"# Language: {self.language_name} ({self.language_code})\n\n")

            for t in unique_trans:
                original = t.get('text', t.get('original_text', ''))
                translated = t.get('translated', t.get('translated_text', ''))
                line_number = t.get('line', t.get('line_number', 0))
                speaker = t.get('speaker', '')

                if not self._is_valid_translation(original, translated):
                    continue

                original_escaped = escape_quotes_renpy(original)
                translated_escaped = escape_quotes_renpy(translated)
                block_id = self._generate_block_id(original, line_number, speaker)

                # === ПРАВИЛЬНЫЙ ФОРМАТ REN'PY TRANSLATE BLOCK ===
                f.write(f"# game/{original_file}:{line_number}\n")
                f.write(f"translate {self.language_code} {block_id}:\n")
                if speaker:
                    f.write(f'    # {speaker} "{original_escaped}"\n')
                    f.write(f'    {speaker} "{translated_escaped}"\n')
                else:
                    f.write(f'    # "{original_escaped}"\n')
                    f.write(f'    "{translated_escaped}"\n')
                f.write("\n")

        logger.info(f"Создан файл перевода: {translation_file_path} ({len(unique_trans)} блоков)")

    def _generate_common_rpy(self, output_dir: Path, strings: List[Dict]):
        """
        Генерирует common.rpy с translate strings (old/new формат).
        Используется для строк интерфейса и меню.
        """
        common_path = output_dir / "common.rpy"

        # Убираем дубликаты
        seen: Set[str] = set()
        unique = []
        for t in strings:
            orig = t.get('text', t.get('original_text', ''))
            if orig and orig not in seen and not is_file_path(orig):
                seen.add(orig)
                unique.append(t)

        with open(common_path, 'w', encoding='utf-8') as f:
            f.write("# Common strings translation\n")
            f.write(f"# Generated by TranslatorPro V3\n\n")
            f.write(f"translate {self.language_code} strings:\n\n")

            for t in unique:
                original = t.get('text', t.get('original_text', ''))
                translated = t.get('translated', t.get('translated_text', ''))

                if not self._is_valid_translation(original, translated):
                    continue

                original_escaped = escape_quotes_renpy(original)
                translated_escaped = escape_quotes_renpy(translated)

                f.write(f'    old "{original_escaped}"\n')
                f.write(f'    new "{translated_escaped}"\n\n')

        logger.info(f"Создан common.rpy: {common_path} ({len(unique)} строк)")

    def _generate_screens_rpy(self, output_dir: Path, strings: List[Dict]):
        """
        Генерирует screens.rpy для перевода экранов (screen statements).
        """
        screens_path = output_dir / "screens.rpy"

        # Фильтруем только строки из screens.rpy
        screen_strings = [t for t in strings if 'screen' in t.get('file', '').lower()]

        if not screen_strings:
            # Создаём пустой файл-заглушку
            with open(screens_path, 'w', encoding='utf-8') as f:
                f.write("# Screens translation (placeholder)\n")
                f.write(f"# Generated by TranslatorPro V3\n\n")
                f.write(f"translate {self.language_code} strings:\n\n")
            logger.info(f"Создан screens.rpy (пустой): {screens_path}")
            return

        seen: Set[str] = set()
        with open(screens_path, 'w', encoding='utf-8') as f:
            f.write("# Screens translation\n")
            f.write(f"# Generated by TranslatorPro V3\n\n")
            f.write(f"translate {self.language_code} strings:\n\n")

            for t in screen_strings:
                original = t.get('text', t.get('original_text', ''))
                translated = t.get('translated', t.get('translated_text', ''))

                if not original or original in seen or not self._is_valid_translation(original, translated):
                    continue
                seen.add(original)

                original_escaped = escape_quotes_renpy(original)
                translated_escaped = escape_quotes_renpy(translated)

                f.write(f'    old "{original_escaped}"\n')
                f.write(f'    new "{translated_escaped}"\n\n')

        logger.info(f"Создан screens.rpy: {screens_path} ({len(seen)} строк)")

    def generate_single_rpy(self, output_path: Path, original_file: str,
                            translations: List[Dict], with_comments: bool = True) -> Path:
        """
        Генерирует один .rpy файл перевода (для тестов и отдельных файлов).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# Russian translation of {original_file}\n")
            f.write(f"# Generated by TranslatorPro V3\n")
            f.write(f"# WARNING: This is an unsanctioned fan translation.\n\n")

            # Dialogue blocks
            dialogues = [t for t in translations if t.get('type') == 'dialogue']
            menus = [t for t in translations if t.get('type') == 'menu']
            others = [t for t in translations if t.get('type') not in ('dialogue', 'menu')]

            if dialogues or menus:
                for t in sorted(dialogues + menus, key=lambda x: x.get('line', 0)):
                    original = t.get('text', '')
                    translated = t.get('translated', '')
                    line_number = t.get('line', 0)
                    speaker = t.get('speaker', '')

                    if not original or not translated:
                        continue

                    block_id = self._generate_block_id(original, line_number, speaker)

                    f.write(f"# game/{original_file}:{line_number}\n")
                    f.write(f"translate {self.language_code} {block_id}:\n")

                    orig_esc = escape_quotes_renpy(original)
                    trans_esc = escape_quotes_renpy(translated)

                    if with_comments:
                        if speaker:
                            f.write(f'    # {speaker} "{orig_esc}"\n')
                        else:
                            f.write(f'    # "{orig_esc}"\n')

                    if speaker:
                        f.write(f'    {speaker} "{trans_esc}"\n')
                    else:
                        f.write(f'    "{trans_esc}"\n')
                    f.write("\n")

            # Strings block
            if others:
                f.write(f"translate {self.language_code} strings:\n\n")
                seen: Set[str] = set()
                for t in others:
                    original = t.get('text', '')
                    translated = t.get('translated', '')

                    if not original or not translated or original in seen:
                        continue
                    seen.add(original)

                    orig_esc = escape_quotes_renpy(original)
                    trans_esc = escape_quotes_renpy(translated)

                    f.write(f'    old "{orig_esc}"\n')
                    f.write(f'    new "{trans_esc}"\n\n')

        logger.info(f"Создан single .rpy: {output_path}")
        return output_path
