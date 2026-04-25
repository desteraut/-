#!/usr/bin/env python3
"""
Конвертер scripts.txt → .rpy файлы Ren'Py

scripts.txt содержит диалоги в формате:
    filename.rpy:line_number | character "dialogue text"

Этот скрипт разбивает файл на отдельные .rpy файлы.

Использование:
    python txt_to_rpy.py <scripts.txt> <output_dir>
"""

import os
import sys
import re
from collections import defaultdict


def parse_scripts_txt(filepath: str) -> dict:
    """
    Парсит scripts.txt и возвращает словарь {filename: [(line_num, character, dialogue), ...]}
    """
    entries = defaultdict(list)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Регулярное выражение для парсинга:
    # filename.rpy:123 | e "dialogue text"
    # или:
    # filename.rpy:123 | "dialogue text"
    pattern = re.compile(
        r'^([\w_]+\.rpy):(\d+)\s*\|\s*(?:(\w+)\s+)?"(.+)"\s*$',
        re.MULTILINE
    )
    
    for match in pattern.finditer(content):
        filename = match.group(1)
        line_num = int(match.group(2))
        character = match.group(3) or "e"  # по умолчанию "e"
        dialogue = match.group(4)
        entries[filename].append((line_num, character, dialogue))
    
    return dict(entries)


def convert_to_rpy(entries: dict, output_dir: str):
    """
    Создает .rpy файлы из распарсенных записей.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for filename, lines in sorted(entries.items()):
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {filename}\n")
            f.write(f"# Auto-generated from scripts.txt\n")
            f.write(f"# Total lines: {len(lines)}\n\n")
            
            for line_num, character, dialogue in sorted(lines, key=lambda x: x[0]):
                # Экранируем кавычки внутри диалога
                escaped = dialogue.replace('"', '\\"')
                f.write(f"    {character} \"{escaped}\"\n")
        
        print(f"  ✅ {filename} ({len(lines)} строк)")


def main():
    if len(sys.argv) < 3:
        print("Использование: python txt_to_rpy.py <scripts.txt> <output_dir>")
        print("")
        print("Если scripts.txt содержит 'None' или пуст:")
        print("  1. Убедитесь, что файл корректно экспортирован")
        print("  2. Или используйте .rpy файлы напрямую из папки scripts/")
        sys.exit(1)
    
    scripts_txt = sys.argv[1]
    output_dir = sys.argv[2]
    
    # Проверка файла
    if not os.path.exists(scripts_txt):
        print(f"❌ Файл не найден: {scripts_txt}")
        sys.exit(1)
    
    with open(scripts_txt, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    if content == 'None' or not content:
        print(f"⚠️  Файл {scripts_txt} пуст или содержит 'None'")
        print("   Убедитесь, что файл корректно экспортирован из .rpa архива.")
        print("   Для распаковки .rpa используйте:")
        print("     python scripts/check_unrpa.py")
        print("     python -m unrpa <файл.rpa> -p <выходная_папка>")
        sys.exit(1)
    
    print(f"📖 Чтение {scripts_txt}...")
    entries = parse_scripts_txt(scripts_txt)
    
    if not entries:
        print("❌ Не удалось распарсить файл. Проверьте формат.")
        sys.exit(1)
    
    print(f"📁 Найдено {len(entries)} файлов, {sum(len(v) for v in entries.values())} строк диалогов")
    print(f"📂 Создание .rpy файлов в {output_dir}...\n")
    
    convert_to_rpy(entries, output_dir)
    
    print(f"\n✅ Конвертация завершена!")


if __name__ == "__main__":
    main()
