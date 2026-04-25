#!/usr/bin/env python3
"""
Проверка установки unrpa
"""
import sys
import importlib

print("=" * 60)
print("ПРОВЕРКА UNRPA")
print("=" * 60)

print(f"\n📁 Python: {sys.executable}")
print(f"📋 Версия: {sys.version}")

print("\n🔍 Проверка импортов...")

# Проверка 1: Базовый импорт
try:
    import unrpa
    print(f"✅ import unrpa — OK")
    print(f"   Путь: {unrpa.__file__}")
except ImportError as e:
    print(f"❌ import unrpa — {e}")

# Проверка 2: Из подмодуля
try:
    from unrpa import unrpa
    print(f"✅ from unrpa import unrpa — OK")
except ImportError as e:
    print(f"❌ from unrpa import unrpa — {e}")

# Проверка 3: UnRPA класс
try:
    from unrpa.unrpa import UnRPA
    print(f"✅ from unrpa.unrpa import UnRPA — OK")
except ImportError as e:
    print(f"❌ from unrpa.unrpa import UnRPA — {e}")

# Проверка 4: pip show
print("\n📦 Информация из pip:")
try:
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pip", "show", "unrpa"], 
                          capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f"❌ Ошибка: {e}")

print("=" * 60)