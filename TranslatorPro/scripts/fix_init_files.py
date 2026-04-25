#!/usr/bin/env python3
"""
scripts/fix_init_files.py
Автоматическое исправление all = на __all__ = и name на __name__
"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def fix_all_to_dunder_all(file_path: Path) -> int:
    """Исправляет all = на __all__ ="""
    content = file_path.read_text(encoding='utf-8')
    
    # Ищем all = но не __all__ =
    pattern = r'^all\s*=\s*\['
    if re.search(pattern, content, re.MULTILINE) and '__all__' not in content:
        new_content = re.sub(pattern, '__all__ = [', content, flags=re.MULTILINE)
        file_path.write_text(new_content, encoding='utf-8')
        return 1
    return 0

def fix_logger_name(file_path: Path) -> int:
    """Исправляет getLogger(name) на getLogger(__name__)"""
    content = file_path.read_text(encoding='utf-8')
    
    # Ищем getLogger(name) но не getLogger(__name__)
    if 'logging.getLogger(name)' in content and 'logging.getLogger(__name__)' not in content:
        new_content = content.replace('logging.getLogger(name)', 'logging.getLogger(__name__)')
        file_path.write_text(new_content, encoding='utf-8')
        return 1
    return 0

def main():
    fixed_all = 0
    fixed_logger = 0
    
    print("🔧 Исправление файлов...\n")
    
    for py_file in PROJECT_ROOT.rglob('*.py'):
        # Пропускаем venv и __pycache__
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue
        
        # Исправляем __init__.py
        if py_file.name == '__init__.py':
            fixed = fix_all_to_dunder_all(py_file)
            if fixed:
                print(f"  ✅ {py_file.relative_to(PROJECT_ROOT)} (all → __all__)")
                fixed_all += fixed
        
        # Исправляем logger во всех .py файлах
        fixed = fix_logger_name(py_file)
        if fixed:
            print(f"  ✅ {py_file.relative_to(PROJECT_ROOT)} (name → __name__)")
            fixed_logger += fixed
    
    print(f"\n{'='*60}")
    print(f"✅ Исправлено {fixed_all} файлов (all → __all__)")
    print(f"✅ Исправлено {fixed_logger} файлов (name → __name__)")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()