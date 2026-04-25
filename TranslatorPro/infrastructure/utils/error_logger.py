"""
ErrorLogger — централизованная система логирования ошибок перевода.
Сохраняет все ошибки в единый файл в папке программы.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TranslationError:
    """Запись об ошибке перевода."""
    timestamp: str
    module: str           # Модуль, где произошла ошибка
    severity: str         # ERROR, WARNING, CRITICAL
    error_type: str       # Тип ошибки (translation_failed, integrity_check_failed, etc.)
    message: str          # Сообщение об ошибке
    details: str          # Подробности
    file: str = ""        # Файл, связанный с ошибкой
    line: int = 0         # Строка
    original_text: str = ""  # Оригинальный текст
    recovery_hint: str = ""  # Рекомендация по исправлению


class ErrorLogger:
    """
    Централизованный логгер ошибок перевода.
    Сохраняет все ошибки в JSON и текстовый файл в папке logs/ программы.
    """

    def __init__(self, log_dir: Optional[Path] = None):
        """
        Args:
            log_dir: Директория для логов (по умолчанию PROJECT_ROOT/logs)
        """
        if log_dir is None:
            # Определяем корень проекта относительно этого файла
            self.log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        else:
            self.log_dir = Path(log_dir)

        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.error_log_file = self.log_dir / "errors.json"
        self.error_txt_file = self.log_dir / "errors.txt"
        self.errors: List[TranslationError] = []
        self._stats = {
            "total_errors": 0,
            "total_warnings": 0,
            "total_critical": 0,
            "by_module": {},
            "by_type": {}
        }

    def log_error(self, error_type: str, message: str, details: str = "",
                  file: str = "", line: int = 0, original_text: str = "",
                  module: str = "unknown", recovery_hint: str = ""):
        """Логирует ошибку перевода."""
        error = TranslationError(
            timestamp=datetime.now().isoformat(),
            module=module,
            severity="ERROR",
            error_type=error_type,
            message=message,
            details=details,
            file=file,
            line=line,
            original_text=original_text,
            recovery_hint=recovery_hint
        )
        self.errors.append(error)
        self._stats["total_errors"] += 1
        self._stats["by_module"][module] = self._stats["by_module"].get(module, 0) + 1
        self._stats["by_type"][error_type] = self._stats["by_type"].get(error_type, 0) + 1
        self._save()
        logger.error(f"[{module}] {error_type}: {message} | {details}")

    def log_warning(self, error_type: str, message: str, details: str = "",
                    file: str = "", line: int = 0, original_text: str = "",
                    module: str = "unknown", recovery_hint: str = ""):
        """Логирует предупреждение."""
        error = TranslationError(
            timestamp=datetime.now().isoformat(),
            module=module,
            severity="WARNING",
            error_type=error_type,
            message=message,
            details=details,
            file=file,
            line=line,
            original_text=original_text,
            recovery_hint=recovery_hint
        )
        self.errors.append(error)
        self._stats["total_warnings"] += 1
        self._stats["by_module"][module] = self._stats["by_module"].get(module, 0) + 1
        self._stats["by_type"][error_type] = self._stats["by_type"].get(error_type, 0) + 1
        self._save()
        logger.warning(f"[{module}] {error_type}: {message}")

    def log_critical(self, error_type: str, message: str, details: str = "",
                     file: str = "", line: int = 0, original_text: str = "",
                     module: str = "unknown", recovery_hint: str = ""):
        """Логирует критическую ошибку."""
        error = TranslationError(
            timestamp=datetime.now().isoformat(),
            module=module,
            severity="CRITICAL",
            error_type=error_type,
            message=message,
            details=details,
            file=file,
            line=line,
            original_text=original_text,
            recovery_hint=recovery_hint
        )
        self.errors.append(error)
        self._stats["total_critical"] += 1
        self._stats["by_module"][module] = self._stats["by_module"].get(module, 0) + 1
        self._stats["by_type"][error_type] = self._stats["by_type"].get(error_type, 0) + 1
        self._save()
        logger.critical(f"[{module}] CRITICAL {error_type}: {message}")

    def _save(self):
        """Сохраняет ошибки в файлы."""
        # JSON формат
        try:
            data = [asdict(e) for e in self.errors]
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Не удалось сохранить JSON лог: {e}")

        # Текстовый формат
        try:
            lines = [
                "=" * 70,
                "TRANSLATORPRO ERROR LOG",
                f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total: {len(self.errors)} entries",
                "=" * 70,
                ""
            ]

            for i, e in enumerate(self.errors, 1):
                lines.extend([
                    f"--- Error #{i} [{e.severity}] ---",
                    f"Time:     {e.timestamp}",
                    f"Module:   {e.module}",
                    f"Type:     {e.error_type}",
                    f"Message:  {e.message}",
                    f"Details:  {e.details}",
                ])
                if e.file:
                    lines.append(f"File:     {e.file}:{e.line}")
                if e.original_text:
                    lines.append(f"Original: {e.original_text[:100]}")
                if e.recovery_hint:
                    lines.append(f"Hint:     {e.recovery_hint}")
                lines.append("")

            lines.extend([
                "=" * 70,
                f"STATS: Errors={self._stats['total_errors']}, "
                f"Warnings={self._stats['total_warnings']}, "
                f"Critical={self._stats['total_critical']}",
                "=" * 70
            ])

            with open(self.error_txt_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

        except Exception as e:
            logger.error(f"Не удалось сохранить текстовый лог: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику ошибок."""
        return self._stats.copy()

    def get_errors(self) -> List[TranslationError]:
        """Возвращает все ошибки."""
        return self.errors.copy()

    def clear(self):
        """Очищает лог ошибок."""
        self.errors.clear()
        self._stats = {
            "total_errors": 0,
            "total_warnings": 0,
            "total_critical": 0,
            "by_module": {},
            "by_type": {}
        }
        self._save()
        logger.info("Лог ошибок очищен")
