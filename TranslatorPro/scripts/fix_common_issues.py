#!/usr/bin/env python3
"""
scripts/fix_common_issues.py
Автоматическое исправление частых проблем в коде

Использование:
    python scripts/fix_common_issues.py --dry-run  # Только показать
    python scripts/fix_common_issues.py            # Исправить
"""
import sys
import re
from pathlib import Path
from typing import List

class CodeFixer:
    """Автоматическое исправление кода"""
    
    def __init__(self, project_root: Path, dry_run: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.fixed_files: List[str] = []
    
    def fix_logger_name(self, file_path: Path) -> bool:
        """Исправляет logging.getLogger(__name__) → logging.getLogger(__name__)"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # ✅ Ищем и заменяем
            if 'logging.getLogger(__name__)' in content:
                new_content = content.replace(
                    'logging.getLogger(__name__)',
                    'logging.getLogger(__name__)'
                )
                
                if not self.dry_run:
                    file_path.write_text(new_content, encoding='utf-8')
                
                self.fixed_files.append(str(file_path))
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️  Не удалось обработать {file_path}: {e}")
            return False
    
    def fix_all_files(self):
        """Исправляет все файлы в проекте"""
        print(f"\n🔧 Поиск проблемных файлов...\n")
        
        for py_file in self.project_root.rglob('*.py'):
            # Пропускаем виртуальные окружения и кэш
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            if self.fix_logger_name(py_file):
                status = "ИСПРАВЛЕНО" if not self.dry_run else "ТРЕБУЕТ ИСПРАВЛЕНИЯ"
                print(f"  {status}: {py_file.relative_to(self.project_root)}")
        
        print(f"\n{'='*60}")
        if self.dry_run:
            print(f"📝 Найдено {len(self.fixed_files)} файлов для исправления")
            print(f"💡 Запустите без --dry-run для автоматического исправления")
        else:
            print(f"✅ Исправлено {len(self.fixed_files)} файлов")
        print(f"{'='*60}\n")


def main():
    dry_run = '--dry-run' in sys.argv
    project_root = Path(__file__).resolve().parent.parent
    
    fixer = CodeFixer(project_root, dry_run=dry_run)
    fixer.fix_all_files()


if __name__ == '__main__':
    main()