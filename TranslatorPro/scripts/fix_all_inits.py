#!/usr/bin/env python3
"""
scripts/fix_all_inits.py
Исправляет all = на __all__ = во всех __init__.py файлах
"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def fix_init_file(file_path: Path) -> bool:
    """Исправляет all = на __all__ = в файле"""
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Ищем all = но не __all__ =
        if re.search(r'^all\s*=\s*\[', content, re.MULTILINE):
            if '__all__' not in content:
                new_content = re.sub(
                    r'^all\s*=\s*\[',
                    '__all__ = [',
                    content,
                    flags=re.MULTILINE
                )
                file_path.write_text(new_content, encoding='utf-8')
                return True
    
    except Exception as e:
        print(f"⚠️  Ошибка обработки {file_path}: {e}")
    
    return False

def main():
    fixed_count = 0
    
    print("🔧 Исправление __init__.py файлов...\n")
    
    for init_file in PROJECT_ROOT.rglob('__init__.py'):
        # Пропускаем venv и __pycache__
        if 'venv' in str(init_file) or '__pycache__' in str(init_file):
            continue
        
        if fix_init_file(init_file):
            print(f"  ✅ {init_file.relative_to(PROJECT_ROOT)}")
            fixed_count += 1
    
    print(f"\n{'='*60}")
    print(f"✅ Исправлено {fixed_count} файлов")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()