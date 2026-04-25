#!/usr/bin/env python3
"""
scripts/quick_check.py
Быстрая проверка критических импортов для CI/CD

Использование:
    python scripts/quick_check.py

Возвращает:
    0 — все критические импорты успешны
    1 — найдены критические ошибки
"""
import sys
import importlib
from pathlib import Path

def check_critical_imports():
    """Проверяет только критические импорты"""
    critical = [
        'config',
        'domain',
        'application',
        'infrastructure',
        'ports',
    ]
    
    failed = []
    
    for module in critical:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n❌ Критические ошибки: {', '.join(failed)}")
        return False
    
    print("\n✅ Все критические импорты успешны!")
    return True


if __name__ == '__main__':
    success = check_critical_imports()
    sys.exit(0 if success else 1)