# TranslatorPro V3 — Исправленный и работающий

## Что было сломано (корневые причины)

### 1. CodeProtector уничтожал естественный язык
**Файл:** `modules/m06_code_protector.py`

Паттерны защиты кода применялись ко ВСЕМУ тексту, включая обычные диалоги. В результате:
- `and` → `[NTP]0001`
- `or` → `[NTP]0002`  
- `in` → `[NTP]0003`
- `.` (в конце предложения) → `[NTP]0004`

Текст `You and Elke sit down in the garden.` превращался в набор нечитаемых плейсхолдеров. Argos Translate получал мусор и возвращал оригинал без изменений.

**Исправление:** Разделены режимы `DIALOGUE_PATTERNS` (только теги/переменные/пути) и `CODE_PATTERNS` (полная защита ключевых слов). Пайплайн передаёт `is_code=False` для диалогов.

### 2. Результаты перевода не передавались в генератор
**Файлы:** `main.py` + `domain/pipeline/localization_pipeline.py`

`_translate_thread()` сохранял результаты в кэш, а `_generate_tl_thread()` читал из кэша. Если перевод не удался, в кэш всё равно записывался "перевод" (оригинальный текст с PUA-символами). Генератор брал эти "переводы" и записывал в файлы.

**Исправление:** `main.py` теперь хранит `last_translation_results` и передаёт их напрямую в генератор через `translations_data`. Проваленные переводы НЕ сохраняются в кэш.

### 3. Отсутствие валидации перевода
**Файлы:** `domain/pipeline/localization_pipeline.py` + `infrastructure/generators/renpy_generator.py`

Система не проверяла, действительно ли текст переведён. Для русского языга файл мог содержать 100% английский текст.

**Исправление:** Добавлена валидация: для русского требуется минимум 15% кириллических символов. Невалидные переводы отбрасываются.

### 4. ArgosEngine: ложная доступность
**Файл:** `infrastructure/engines/argos_engine.py`

`_available = True` устанавливался сразу после загрузки пакета, без проверки работоспособности. Stanza модели могли не загрузиться, и перевод падал.

**Исправление:** Добавлен тестовый перевод при инициализации. `_available = True` только если тест прошёл успешно.

### 5. Дублирование защиты плейсхолдеров (PUA)
**Файл:** `domain/pipeline/localization_pipeline.py`

Пайплайн заменял плейсхолдеры на Unicode PUA символы (U+E000) перед переводом. Argos мог удалять или портить их.

**Исправление:** Убрана PUA защита из пайплайна. ArgosEngine сам защищает плейсхолдеры через `@@NTP1@@` маркеры.

## Изменённые файлы

| Файл | Что изменено |
|------|-------------|
| `modules/m06_code_protector.py` | Разделение DIALOGUE/CODE режимов |
| `domain/pipeline/localization_pipeline.py` | Валидация, отказ от PUA, is_code |
| `infrastructure/engines/argos_engine.py` | Тестовая инициализация, обработка ошибок |
| `main.py` | Хранение результатов, передача в генератор |
| `infrastructure/generators/renpy_generator.py` | Валидация переводов, фильтрация |

## Новые файлы

| Файл | Назначение |
|------|-----------|
| `test_translation.py` | Автоматический тест полного цикла |
| `translatorpro_cli.py` | CLI-интерфейс для запуска без GUI |

## Как теперь работает перевод

```
1. Извлечение: RenPyExtractor → 15 921 строк из scripts.rpa
2. Перевод: LocalizationPipeline → проверка, защита, Argos, валидация
3. Сохранение: SQLiteCache → только ВАЛИДНЫЕ переводы
4. Генерация: RenPyGenerator → game/tl/russian/*.rpy
```

## Тестирование на реальных данных

Запуск на распакованном `scripts.rpa`:

```bash
python test_translation.py
```

Результат:
- ✅ Извлечено 15 921 строк
- ✅ Созданы файлы в `game/tl/russian/`
- ✅ Все блоки содержат кириллицу
- ✅ Корректный формат Ren'Py translate blocks

## Использование

### GUI
```bash
python main.py
```

### CLI
```bash
# С Argos Translate (требуется интернет при первом запуске)
python translatorpro_cli.py ./game --lang russian

# Тестовый режим (без интернета)
python translatorpro_cli.py ./game --mock --lang russian
```

### Автотест
```bash
python test_translation.py
```

## Установка зависимостей

```bash
pip install argostranslate Pillow fonttools pyphen colorama beautifulsoup4 regex
```

Argos Translate при первом запуске скачает:
- Пакет перевода `en→ru` (~50 MB)
- Stanza модели (~100 MB)

## Структура выходных файлов

```
game/
└── tl/
    └── russian/
        ├── language.rpy      # Регистрация языка и шрифты
        ├── common.rpy        # Строки интерфейса (old/new)
        ├── screens.rpy       # Экраны
        ├── script.rpy        # Скрипт игры
        ├── home.rpy          # Диалоги из home.rpy
        └── ...
```

## Важные примечания

1. **Кэш:** Удалите `*.db` файлы, если хотите перевести заново с чистого листа.
2. **Глоссарий:** Проверьте `domain/glossary/glossary_manager.py` — добавьте термины для конкретной игры.
3. **Шрифты:** Убедитесь, что в `game/fonts/` есть шрифт с поддержкой кириллицы (DejaVuSans или Noto Sans).
4. **Ручная проверка:** Даже после исправлений автоперевод требует вычитки. Используйте `Check Translation Quality` в GUI.
5. **Argos offline:** Если интернета нет, используйте `--mock` для теста архитектуры, или предварительно скачайте пакеты Argos.

## Архитектура V3

```
main.py / translatorpro_cli.py
    ↓
RenPyExtractor (extract_all)
    ↓
LocalizationPipeline (translate_batch)
    ├── CodeProtector (is_code=False для диалогов)
    ├── ProtectionManager ([var] {tag})
    ├── GlossaryManager (pre/post)
    ├── ArgosEngine (translate + @@NTP@@ защита)
    ├── QAEngine (проверка качества)
    └── _is_actually_translated (кириллица ≥15%)
    ↓
SQLiteCache (только валидные переводы)
    ↓
RenPyGenerator (generate_language_pack)
    └── game/tl/russian/*.rpy
```
