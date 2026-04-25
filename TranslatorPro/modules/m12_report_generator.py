"""
m12_report_generator.py — Генерация отчётов
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Генератор отчётов о локализации."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, stats: Dict[str, Any], errors: List[str], output_path: Path = None) -> Path:
        """Генерирует текстовый отчёт."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"translation_report_{timestamp}.txt"

        lines = [
            "=" * 60,
            "TRANSLATION REPORT",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "[SUMMARY]",
        ]
        for key, value in stats.items():
            lines.append(f"  {key}: {value}")

        if errors:
            lines.extend(["", "[ERRORS]"])
            for err in errors:
                lines.append(f"  - {err}")
        else:
            lines.extend(["", "[ERRORS]", "  None"])

        lines.extend(["", "=" * 60])

        report_text = "\n".join(lines)
        output_path.write_text(report_text, encoding="utf-8")
        logger.info(f"📄 Отчёт сохранён: {output_path}")
        return output_path

    def generate_json(self, data: Dict[str, Any], output_path: Path = None) -> Path:
        """Генерирует JSON-отчёт."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.output_dir / f"translation_report_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"📄 JSON отчёт сохранён: {output_path}")
        return output_path
