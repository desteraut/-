#!/usr/bin/env python3
"""
scripts/validate_imports.py
Автоматическая проверка всех импортов проекта TranslatorPro V3.0.0
"""
import sys
import importlib
import importlib.util
import re  # ✅ ДОБАВИТЬ ЭТУ СТРОКУ
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# ✅ ДОБАВЛЕНО: Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

@dataclass
class ImportResult:
    """Результат проверки импорта"""
    module: str
    success: bool
    error: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class ImportValidator:
    """Валидатор импортов проекта"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[ImportResult] = []
        self.skipped: List[str] = []
        
        # ✅ Критические модули (должны импортироваться)
        self.critical_modules = [
            'config',
            'domain',
            'domain.entities',
            'domain.glossary',
            'domain.pipeline',
            'domain.qa',
            'domain.policies',
            'application',
            'application.services',
            'infrastructure',
            'infrastructure.cache',
            'infrastructure.engines',
            'infrastructure.extractors',
            'infrastructure.generators',
            'infrastructure.guards',
            'infrastructure.utils',
            'ports',
        ]
        
        # ✅ Модули с известными проблемами (требуют внешних зависимостей)
        self.optional_modules = [
            'infrastructure.engines.argos_engine',
            'infrastructure.engines.nllb_engine',
            'infrastructure.utils.rpa_extractor',
        ]
        
        # ✅ Файлы для прямой проверки
        self.files_to_check = [
            'config.py',
            'domain/__init__.py',
            'domain/entities/__init__.py',
            'domain/glossary/__init__.py',
            'domain/pipeline/__init__.py',
            'domain/qa/__init__.py',
            'domain/policies/__init__.py',
            'application/__init__.py',
            'application/services/__init__.py',
            'infrastructure/__init__.py',
            'infrastructure/cache/__init__.py',
            'infrastructure/engines/__init__.py',
            'infrastructure/extractors/__init__.py',
            'infrastructure/generators/__init__.py',
            'infrastructure/guards/__init__.py',
            'infrastructure/utils/__init__.py',
            'ports/__init__.py',
        ]
    
    def validate_module(self, module_name: str) -> ImportResult:
        """Проверяет импорт модуля"""
        try:
            importlib.import_module(module_name)
            return ImportResult(module=module_name, success=True)
        except ImportError as e:
            return ImportResult(
                module=module_name,
                success=False,
                error=str(e)
            )
        except Exception as e:
            return ImportResult(
                module=module_name,
                success=False,
                error=f"Unexpected error: {e}"
            )
    
    def validate_file(self, file_path: Path) -> ImportResult:
        """Проверяет файл на синтаксические ошибки"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            compile(source, str(file_path), 'exec')
            return ImportResult(module=str(file_path), success=True)
        except SyntaxError as e:
            return ImportResult(
                module=str(file_path),
                success=False,
                error=f"Syntax error: {e}"
            )
        except Exception as e:
            return ImportResult(
                module=str(file_path),
                success=False,
                error=str(e)
            )
    
    def check_logger_usage(self, file_path: Path) -> List[str]:
        """Проверяет корректность использования logger.getLogger(__name__)"""
        warnings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # ✅ Ищем неправильное использование: getLogger(name) вместо getLogger(__name__)
            if 'logging.getLogger(name)' in content and 'logging.getLogger(__name__)' not in content:
                warnings.append("⚠️  Найдено logging.getLogger(name) — должно быть getLogger(__name__)")
            
            # ✅ Ищем отсутствие импорта logging
            if 'logger = logging.getLogger' in content and 'import logging' not in content:
                warnings.append("⚠️  Отсутствует import logging")
            
            # ✅ Проверяем __all__ вместо all
            if re.search(r'^all\s*=\s*\[', content, re.MULTILINE) and '__all__' not in content:
                warnings.append("⚠️  Найдено 'all =' вместо '__all__ ='")
            
        except Exception as e:
            warnings.append(f"⚠️  Не удалось проверить файл: {e}")
        
        return warnings
    
    def run_full_validation(self) -> bool:
        """Запускает полную валидацию"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}  TranslatorPro V3.0.0 — Валидация импортов{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        print(f"{Colors.BLUE}📁 Project Root: {self.project_root}{Colors.RESET}\n")
        
        # ✅ 1. Проверка критических модулей
        print(f"{Colors.BOLD}📦 Шаг 1/4: Проверка критических модулей{Colors.RESET}\n")
        
        for module in self.critical_modules:
            result = self.validate_module(module)
            self.results.append(result)
            
            if result.success:
                print(f"  {Colors.GREEN}✅{Colors.RESET} {module}")
            else:
                print(f"  {Colors.RED}❌{Colors.RESET} {module}")
                print(f"     {Colors.RED}Ошибка: {result.error}{Colors.RESET}")
        
        # ✅ 2. Проверка файлов на синтаксис
        print(f"\n{Colors.BOLD}📄 Шаг 2/4: Проверка синтаксиса файлов{Colors.RESET}\n")
        
        for file_name in self.files_to_check:
            file_path = self.project_root / file_name
            if file_path.exists():
                result = self.validate_file(file_path)
                
                # ✅ Дополнительная проверка logger
                if file_path.suffix == '.py':
                    logger_warnings = self.check_logger_usage(file_path)
                    result.warnings.extend(logger_warnings)
                
                if result.success:
                    status = f"{Colors.GREEN}✅{Colors.RESET}"
                else:
                    status = f"{Colors.RED}❌{Colors.RESET}"
                
                print(f"  {status} {file_name}")
                
                for warning in result.warnings:
                    print(f"     {Colors.YELLOW}{warning}{Colors.RESET}")
            else:
                print(f"  {Colors.YELLOW}⚠️{Colors.RESET} {file_name} (не найден)")
                self.skipped.append(file_name)
        
        # ✅ 3. Проверка опциональных модулей
        print(f"\n{Colors.BOLD}🔌 Шаг 3/4: Проверка опциональных модулей{Colors.RESET}\n")
        
        for module in self.optional_modules:
            result = self.validate_module(module)
            
            if result.success:
                print(f"  {Colors.GREEN}✅{Colors.RESET} {module} (доступен)")
            else:
                print(f"  {Colors.YELLOW}⚠️{Colors.RESET} {module} (требуется установка зависимостей)")
                print(f"     {Colors.BLUE}Инфо: {result.error}{Colors.RESET}")
        
        # ✅ 4. Проверка зависимостей
        print(f"\n{Colors.BOLD}📋 Шаг 4/4: Проверка зависимостей{Colors.RESET}\n")
        
        dependencies = {
            'argos-translate': 'argostranslate',
            'transformers': 'transformers',
            'torch': 'torch',
            'unrpa': 'unrpa',
            'python-dotenv': 'dotenv',
            'customtkinter': 'customtkinter',
        }
        
        for package, import_name in dependencies.items():
            try:
                importlib.import_module(import_name)
                print(f"  {Colors.GREEN}✅{Colors.RESET} {package}")
            except ImportError:
                print(f"  {Colors.YELLOW}⚠️{Colors.RESET} {package} (не установлен)")
        
        # ✅ Итоговый отчёт
        return self._print_summary()
    
    def _print_summary(self) -> bool:
        """Выводит итоговый отчёт"""
        total = len([r for r in self.results if r.success or not r.module in self.optional_modules])
        failed = len([r for r in self.results if not r.success and r.module not in self.optional_modules])
        warnings = sum(len(r.warnings) for r in self.results)
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}  ИТОГОВЫЙ ОТЧЁТ{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")
        
        print(f"  Всего проверено: {total}")
        print(f"  {Colors.GREEN}✅ Успешно: {total - failed}{Colors.RESET}")
        print(f"  {Colors.RED}❌ Ошибок: {failed}{Colors.RESET}")
        print(f"  {Colors.YELLOW}⚠️  Предупреждений: {warnings}{Colors.RESET}")
        print(f"  {Colors.BLUE}ℹ️  Пропущено: {len(self.skipped)}{Colors.RESET}")
        
        if failed > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}  ❌ ВАЛИДАЦИЯ НЕ ПРОЙДЕНА{Colors.RESET}")
            print(f"  {Colors.RED}Исправьте ошибки перед запуском!{Colors.RESET}\n")
            return False
        elif warnings > 0:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}  ⚠️  ВАЛИДАЦИЯ ПРОЙДЕНА С ПРЕДУПРЕЖДЕНИЯМИ{Colors.RESET}")
            print(f"  {Colors.YELLOW}Рекомендуется исправить предупреждения{Colors.RESET}\n")
            return True
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}  ✅ ВАЛИДАЦИЯ ПРОЙДЕНА УСПЕШНО!{Colors.RESET}")
            print(f"  {Colors.GREEN}Проект готов к запуску!{Colors.RESET}\n")
            return True


def main():
    """Точка входа"""
    validator = ImportValidator(PROJECT_ROOT)
    success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()