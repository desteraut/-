"""
m02_project_manager.py — Управление проектами перевода (.rtp)
Формат .rtp — Ren'Py Translation Project (JSON)
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ProjectManager:
    """
    Модуль m02: Управление проектами локализации.
    Создание, сохранение, загрузка .rtp файлов.
    """
    
    def __init__(self, projects_dir: Optional[Path] = None):
        self.projects_dir = projects_dir or Path.home() / ".translatorpro" / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.current_project: Optional[Dict] = None
    
    def create_project(self, source_path: str, target_language: str = "russian",
                       source_language: str = "english", mt_engine: str = "argos") -> Dict:
        """Создаёт новый проект перевода"""
        project = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "source_path": str(Path(source_path).resolve()),
            "target_language": target_language,
            "source_language": source_language,
            "mt_engine": mt_engine,
            "files": [],
            "font_replacements": [],
            "settings": {
                "replace_fonts": True,
                "add_hyphens": True,
                "fit_text": True,
                "decompile_rpyc": True,
                "extract_rpa": True
            }
        }
        self.current_project = project
        logger.info(f"m02: Создан проект: {source_path} -> {target_language}")
        return project
    
    def add_file(self, filename: str, strings_count: int, translated_count: int = 0, errors: int = 0):
        """Добавляет файл в проект"""
        if not self.current_project:
            raise ValueError("Нет активного проекта")
        
        self.current_project["files"].append({
            "source": filename,
            "status": "pending",
            "strings_count": strings_count,
            "translated_count": translated_count,
            "errors": errors
        })
    
    def update_file_status(self, filename: str, status: str, translated_count: int = None, errors: int = None):
        """Обновляет статус файла"""
        if not self.current_project:
            return
        
        for f in self.current_project["files"]:
            if f["source"] == filename:
                f["status"] = status
                if translated_count is not None:
                    f["translated_count"] = translated_count
                if errors is not None:
                    f["errors"] = errors
                break
    
    def add_font_replacement(self, old_font: str, new_font: str):
        """Добавляет замену шрифта"""
        if not self.current_project:
            return
        
        self.current_project["font_replacements"].append({
            "old": old_font,
            "new": new_font
        })
    
    def save(self, project_path: Optional[Path] = None) -> Path:
        """Сохраняет проект в .rtp файл"""
        if not self.current_project:
            raise ValueError("Нет активного проекта")
        
        if project_path is None:
            # Автоматическое имя файла
            src_name = Path(self.current_project["source_path"]).name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_path = self.projects_dir / f"{src_name}_{timestamp}.rtp"
        
        project_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_project, f, indent=2, ensure_ascii=False)
        
        logger.info(f"m02: Проект сохранён: {project_path}")
        return project_path
    
    def load(self, project_path: Path) -> Dict:
        """Загружает проект из .rtp файла"""
        with open(project_path, 'r', encoding='utf-8') as f:
            self.current_project = json.load(f)
        
        logger.info(f"m02: Проект загружен: {project_path}")
        return self.current_project
    
    def get_summary(self) -> Dict:
        """Возвращает сводку по проекту"""
        if not self.current_project:
            return {}
        
        files = self.current_project["files"]
        total_strings = sum(f["strings_count"] for f in files)
        total_translated = sum(f["translated_count"] for f in files)
        total_errors = sum(f["errors"] for f in files)
        
        return {
            "total_files": len(files),
            "total_strings": total_strings,
            "total_translated": total_translated,
            "total_errors": total_errors,
            "progress_percent": round(total_translated / total_strings * 100, 1) if total_strings > 0 else 0
        }
    
    def list_projects(self) -> List[Path]:
        """Возвращает список всех .rtp файлов"""
        return sorted(self.projects_dir.glob("*.rtp"))
