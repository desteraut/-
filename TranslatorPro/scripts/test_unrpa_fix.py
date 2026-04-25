#!/usr/bin/env python3
"""
scripts/test_unrpa_fix.py
Тест исправленной интеграции unrpa
"""
import sys
from pathlib import Path

# Добавляем проект в path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.utils.rpa_extractor import extract_rpa_with_unrpa

def main():
    # Поиск тестового RPA файла
    test_rpa = None
    for rpa_file in PROJECT_ROOT.rglob("*.rpa"):
        test_rpa = rpa_file
        break
    
    if not test_rpa:
        print("⚠️ RPA файлы не найдены в проекте")
        print("💡 Поместите тестовый .rpa файл в папку проекта для проверки")
        return
    
    output_dir = PROJECT_ROOT / "_test_extract"
    
    print(f"🔄 Тест распаковки: {test_rpa}")
    print(f"📁 Вывод в: {output_dir}")
    
    success = extract_rpa_with_unrpa(str(test_rpa), str(output_dir))
    
    if success:
        print(f"✅ Успех! Файлы извлечены в: {output_dir}")
        # Показать первые 5 извлечённых файлов
        extracted = list(output_dir.rglob("*"))[:5]
        if extracted:
            print("📋 Примеры извлечённых файлов:")
            for f in extracted:
                if f.is_file():
                    print(f"   - {f.relative_to(output_dir)}")
    else:
        print("❌ Ошибка распаковки")
    
    # Очистка
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print(f"🧹 Тестовая папка удалена")

if __name__ == '__main__':
    main()