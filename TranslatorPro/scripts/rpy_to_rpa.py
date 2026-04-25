#!/usr/bin/env python3
"""
Утилита для упаковки .rpy файлов в .rpa архив Ren'Py.

Использование:
    python rpy_to_rpa.py <папка_с_rpy> <выходной_файл.rpa>

Пример:
    python rpy_to_rpa.py ./translated_scripts/ ./scripts.rpa
"""

import os
import sys
import struct
import pickle
import zlib
import hashlib

def pack_rpa(source_dir: str, output_file: str):
    """
    Упаковывает .rpy файлы из source_dir в .rpa архив Ren'Py.
    
    Формат .rpa:
    - Заголовок: "RPA-3.0 <offset_hex>\n"
    - Данные: последовательно записанные zlib-сжатые файлы
    - Таблица индексов: pickle-структура с {filename: [(offset, length, prefix)]}
    """
    if not os.path.isdir(source_dir):
        print(f"❌ Ошибка: {source_dir} не является папкой")
        sys.exit(1)
    
    # Собираем все .rpy файлы
    files_to_pack = []
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            if filename.endswith('.rpy'):
                full_path = os.path.join(root, filename)
                # Относительный путь в архиве
                rel_path = os.path.relpath(full_path, source_dir).replace(os.sep, '/')
                files_to_pack.append((rel_path, full_path))
    
    if not files_to_pack:
        print(f"❌ Ошибка: в {source_dir} не найдено .rpy файлов")
        sys.exit(1)
    
    print(f"📦 Найдено {len(files_to_pack)} .rpy файлов для упаковки")
    
    # Сортируем для детерминированности
    files_to_pack.sort(key=lambda x: x[0])
    
    # Записываем данные
    index = {}
    data_offset = 0
    data_parts = []
    
    for rel_path, full_path in files_to_pack:
        with open(full_path, 'rb') as f:
            content = f.read()
        
        # Сжимаем данные
        compressed = zlib.compress(content, level=6)
        
        # Для RPA-3.0: каждый файл = (offset, length, prefix)
        # prefix = пустые байты в начале (для совместимости с Ren'Py шифрованием)
        prefix = b''
        
        # Добавляем в индекс
        if rel_path not in index:
            index[rel_path] = []
        index[rel_path].append((data_offset, len(compressed), prefix))
        
        data_parts.append(compressed)
        data_offset += len(compressed)
    
    # Объединяем все данные
    data = b''.join(data_parts)
    
    # Сериализуем индекс
    index_data = pickle.dumps(index, protocol=2)
    
    # Общая структура:
    # [заголовок][данные][индекс]
    # offset в заголовке = позиция индекса
    
    header = f"RPA-3.0 {data_offset + len(data):016x}\n".encode('utf-8')
    
    # Записываем архив
    with open(output_file, 'wb') as f:
        f.write(header)
        f.write(data)
        f.write(index_data)
    
    print(f"✅ Архив создан: {output_file}")
    print(f"   Файлов: {len(files_to_pack)}")
    print(f"   Размер данных: {len(data)} байт")
    print(f"   Размер индекса: {len(index_data)} байт")
    print(f"   Общий размер: {os.path.getsize(output_file)} байт")
    
    # Выводим список файлов
    print(f"\n📋 Содержимое архива:")
    for rel_path, _ in files_to_pack:
        print(f"   {rel_path}")

def main():
    if len(sys.argv) < 3:
        print("Использование: python rpy_to_rpa.py <папка_с_rpy> <выходной_файл.rpa>")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    pack_rpa(source_dir, output_file)

if __name__ == "__main__":
    main()
