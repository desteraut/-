# TranslatorPro V3 — Production Localizer для Ren'Py

Версия: 3.0.1 (refactored)

## Что нового в 3.0.1

### Удалено
- **.rpyc поддержка удалена** — бинарные файлы .rpyc/.rpymc вызывали проблемы. Используйте только `.rpy` исходники.
- **Дублирующие модули** — m01_logger, m04_rpyc_decompiler, m05_text_extractor, m07_translator
- **unrpyc** — инструмент декомпиляции .rpyc

### Добавлено
- **ErrorLogger** — централизованный лог ошибок перевода (logs/errors.json + logs/errors.txt)
- **text_utils** — общие утилиты для экстракторов и генераторов (убрано дублирование)
- **Вкладка "Ошибки"** в GUI — просмотр логов ошибок без выхода из программы
- **Кнопка "Распаковать RPA"** — явная распаковка архивов перед переводом

### Исправлено
- Пути — все пути корректно определяются относительно PROJECT_ROOT
- Архитектура — единая Clean Architecture, убран хаос из дублей
- Импорты — все модули импортируются без ошибок

## Установка

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd TranslatorPro

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Запустить
python main.py
```

## Структура проекта

```
TranslatorPro/
├── main.py                          # Точка входа (GUI)
├── config.py                        # Центральная конфигурация
├── requirements.txt                 # Зависимости
├── glossary.txt                     # Файл глоссария
├── logs/                            # Логи
│   ├── rusgameloc.log              # Основной лог
│   ├── errors.json                 # Лог ошибок (JSON)
│   └── errors.txt                  # Лог ошибок (текст)
├── assets/                          # Ресурсы
│   ├── fonts/
│   └── templates/
├── core/                            # Ядро
│   └── event_bus.py
├── domain/                          # Доменный слой
│   ├── entities/
│   ├── glossary/
│   ├── pipeline/
│   ├── policies/
│   └── qa/
├── infrastructure/                  # Инфраструктура
│   ├── cache/                      # Кэш
│   ├── engines/                    # Движки перевода
│   ├── extractors/                 # Экстракторы текста
│   ├── generators/                 # Генераторы файлов
│   ├── guards/                     # Защита кода
│   └── utils/                      # Утилиты
│       ├── logger.py               # Логирование
│       ├── error_logger.py         # Лог ошибок
│       ├── text_utils.py           # Общие текстовые утилиты
│       ├── rpa_extractor.py        # Распаковка RPA
│       └── helpers.py
├── modules/                         # Модули (убраны дубли)
│   ├── m02_project_manager.py
│   ├── m03_rpa_extractor.py
│   ├── m06_code_protector.py
│   ├── m08_text_fitter.py
│   ├── m09_font_manager.py
│   ├── m10_post_processor.py
│   ├── m11_integrity_checker.py
│   └── m12_report_generator.py
├── ports/                          # Интерфейсы (порты)
├── application/                    # Прикладной слой
└── tests/                          # Тесты
```

## Использование

### GUI режим
1. Запустите `python main.py`
2. Выберите папку с игрой (кнопка "Обзор...")
3. Нажмите "Распаковать RPA" если игра запакована
4. Нажмите "Перевести"
5. Нажмите "Генерировать TL"

### Лог ошибок
Все ошибки автоматически сохраняются в:
- `logs/errors.txt` — читаемый текстовый формат
- `logs/errors.json` — машиночитаемый JSON

Просмотр через вкладку "Ошибки" в GUI.

### Глоссарий
- Вкладка "Глоссарий" — управление терминами
- Авто-извлечение терминов из игры
- Сохранение/загрузка glossary.txt

## Требования

- Python 3.10+
- Ren'Py 8.x (для игр)
- Для перевода: Argos Translate (автоустановка) или NLLB

## Лицензия

MIT License
