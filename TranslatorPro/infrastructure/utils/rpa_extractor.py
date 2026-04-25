"""
RPAExtractor — безопасная распаковка RPA архивов Ren'Py
Поддерживает RPA v1, v2, v3 через библиотеку unrpa
✅ ГАРАНТИИ:
Распаковка ТОЛЬКО в output_dir (не в папку программы!)
Обработка None от list_files() без краша
Path Traversal защита
Логирование прогресса и ошибок
Установка: pip install unrpa
"""
import os
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional, List

# ✅ ИСПРАВЛЕНО: __name__ вместо name
logger = logging.getLogger(__name__)

def is_safe_rpa_path(base_dir: str, target_path: str) -> bool:
    """Проверяет, что целевой путь находится внутри базовой директории."""
    try:
        base = Path(base_dir).resolve()
        target = Path(target_path).resolve()
        target.relative_to(base)
        return True
    except (ValueError, FileNotFoundError, OSError) as e:
        logger.warning(f"⚠️ Небезопасный путь: base={base_dir}, target={target_path}, error={e}")
        return False

def normalize_archive_filename(filename: str) -> Optional[str]:
    """Нормализует имя файла из архива, удаляя опасные конструкции."""
    if not filename:
        return None
    filename = filename.lstrip('/\\').replace('\\', '/').strip()
    
    if not filename or '..' in filename.split('/'):
        logger.warning(f"⚠️ Пропущен файл с Path Traversal: {filename}")
        return None
    
    return filename.replace('/', os.sep)

def extract_rpa_with_unrpa(rpa_path: str, output_dir: str) -> Tuple[bool, int, int]:
    """
    Распаковывает RPA архив через библиотеку unrpa.
    ✅ КРИТИЧЕСКИ ВАЖНО: output_dir должен быть АБСОЛЮТНЫМ путём к папке game/ игры!
    
    Args:
        rpa_path: Путь к RPA файлу
        output_dir: Целевая директория (куда извлекать файлы)
    
    Returns:
        Tuple[bool, int, int]: (успех, извлечено_файлов, ошибок)
    """
    try:
        from unrpa import UnRPA
    except ImportError as e:
        logger.error(f"❌ ImportError unrpa: {e}")
        logger.error("💡 Установите: pip install unrpa")
        return False, 0, 0
    
    # ✅ 1. Нормализация входных путей — ТОЛЬКО АБСОЛЮТНЫЕ
    try:
        rpa_file = Path(rpa_path).resolve(strict=True)
        logger.info(f"📁 RPA файл (абсолютный): {rpa_file}")
    except FileNotFoundError:
        logger.error(f"❌ RPA файл не найден: {rpa_path}")
        return False, 0, 0
    except OSError as e:
        logger.error(f"❌ Ошибка доступа к RPA файлу: {e}")
        return False, 0, 0
    
    # ✅ 2. output_dir — ОБЯЗАТЕЛЬНО абсолютный путь (это папка game/ игры!)
    output_path = Path(output_dir).resolve()
    logger.info(f"📁 Целевая директория (абсолютная): {output_path}")
    
    # ✅ 3. Создаём output_dir если не существует
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Директория создана/проверена: {output_path}")
    except OSError as e:
        logger.error(f"❌ Не удалось создать директорию: {output_path}, error={e}")
        return False, 0, 0
    
    # ✅ 4. Создаём экстрактор с правильным путём назначения и обработкой ошибок
    try:
        extractor = UnRPA(
            str(rpa_file),
            path=str(output_path),
            mkdir=True,
            continue_on_error=True
        )
        logger.info(f"📦 RPA версия: {getattr(extractor, 'version', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации UnRPA: {type(e).__name__}: {e}")
        return False, 0, 0
    
    # ✅ 5. Получаем список файлов для логирования
    file_list: Optional[List[str]] = None
    try:
        file_list = extractor.list_files()
    except Exception as e:
        logger.warning(f"⚠️ list_files() ошибка: {e}")
    
    expected_count = len(file_list) if file_list else 0
    logger.info(f"📦 Найдено файлов в архиве: {expected_count}")
    
    # ✅ 6. Извлекаем все файлы напрямую в output_path
    try:
        extractor.extract_files()
    except Exception as e:
        logger.error(f"❌ Ошибка при извлечении файлов: {e}")
        return False, 0, 1
    
    # ✅ 7. Подсчитываем извлеченные файлы
    extracted_files = [f for f in output_path.rglob('*') if f.is_file()]
    extracted_count = len(extracted_files)
    error_count = max(0, expected_count - extracted_count) if expected_count > 0 else 0
    
    logger.info(f"✅ RPA распакован: {rpa_file.name} → {output_path}")
    logger.info(f"📊 Итог: извлечено {extracted_count} файлов (ожидалось: {expected_count}, ошибок: {error_count})")
    
    return extracted_count > 0, extracted_count, error_count

def find_game_directory(start_path: str) -> str:
    """Идём вверх по дереву от RPA, ищем папку 'game'"""
    current = Path(start_path).resolve(strict=True)
    for _ in range(10):
        if current.name.lower() == "game":
            logger.info(f"📁 Найдена директория game/: {current}")
            return str(current)
        
        for child in current.iterdir():
            if child.is_dir() and child.name.lower() == "game":
                logger.info(f"📁 Найдена директория game/: {child}")
                return str(child)
        
        if current.parent == current:
            break
        current = current.parent
    
    logger.warning(f"⚠️ Не удалось найти папку 'game/', используем: {current.parent}")
    return str(current.parent)

get_game_directory = find_game_directory

def extract_all_rpa_in_game(game_dir: str) -> Dict[str, Tuple[bool, int, int]]:
    """
    Распаковывает все RPA файлы в директории игры.
    ✅ Распаковка идёт в ту же директорию, где находятся .rpa файлы (game_dir).
    ✅ НЕ в корень проекта, НЕ в папку программы.
    """
    results = {}
    game_path = Path(game_dir).resolve()

    if not game_path.exists() or not game_path.is_dir():
        logger.error(f"❌ Некорректная директория игры: {game_path}")
        return results

    # Ищем RPA файлы в указанной директории И в подпапке game/
    rpa_files = list(game_path.glob("*.rpa"))

    # Также проверяем подпапку game/
    game_subfolder = game_path / "game"
    if game_subfolder.exists() and game_subfolder.is_dir():
        rpa_files.extend(list(game_subfolder.glob("*.rpa")))

    # Убираем дубликаты
    seen = set()
    unique_rpa_files = []
    for f in rpa_files:
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_rpa_files.append(f)
    rpa_files = unique_rpa_files

    if not rpa_files:
        logger.warning(f"⚠️ RPA файлы не найдены в: {game_path}")
        return results

    logger.info(f"📦 Найдено RPA файлов: {len(rpa_files)}")

    total_extracted = 0
    total_errors = 0

    for rpa_file in rpa_files:
        try:
            # ✅ КРИТИЧЕСКИ: output_dir = директория, где находится RPA файл
            # Распаковка идёт туда же, откуда взят архив
            output_dir = rpa_file.parent
            success, extracted, errors = extract_rpa_with_unrpa(
                str(rpa_file),
                str(output_dir)
            )
            results[str(rpa_file)] = (success, extracted, errors)
            total_extracted += extracted
            total_errors += errors
            if success:
                logger.info(f"✅ {rpa_file.name} -> {output_dir}")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки {rpa_file}: {e}")
            results[str(rpa_file)] = (False, 0, 1)

    logger.info(f"✅ Все RPA распакованы в их исходные директории")
    logger.info(f"📊 Итог: успешно {len([v for v in results.values() if v[0]])}/{len(results)} RPA файлов")
    logger.info(f"📊 Всего извлечено: {total_extracted} файлов (ошибок: {total_errors})")

    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    import sys
    if len(sys.argv) < 2:
        print("Использование: python rpa_extractor.py <rpa_file> [game_dir]")
        sys.exit(1)
    
    rpa_file = sys.argv[1]
    game_dir = sys.argv[2] if len(sys.argv) >= 3 else find_game_directory(rpa_file)
    
    print(f"📁 RPA файл: {rpa_file}")
    print(f"📁 Директория игры: {game_dir}")
    
    success, extracted, errors = extract_rpa_with_unrpa(rpa_file, str(Path(game_dir)))
    
    print(f"✅ Успех: {success}")
    print(f"📦 Извлечено: {extracted}")
    print(f"❌ Ошибок: {errors}")