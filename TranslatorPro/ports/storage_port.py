"""
ports/storage_port.py
Интерфейс для хранилища заданий (Storage Port)
Clean Architecture - Domain Layer
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from domain.entities.job import TranslationJob


class StoragePort(ABC):
    """Базовый интерфейс для хранилища заданий"""
    
    @abstractmethod
    def save_job(self, job: TranslationJob) -> bool:
        """Сохраняет новое задание"""
        pass
    
    @abstractmethod
    def update_job(self, job: TranslationJob) -> bool:
        """Обновляет существующее задание"""
        pass
    
    @abstractmethod
    def get_job(self, job_id: str) -> Optional[TranslationJob]:
        """Получает задание по ID"""
        pass
    
    @abstractmethod
    def get_jobs_by_status(self, status: str) -> List[TranslationJob]:
        """Получает задания по статусу"""
        pass
    
    @abstractmethod
    def get_all_jobs(self) -> List[TranslationJob]:
        """Получает все задания"""
        pass
    
    @abstractmethod
    def delete_job(self, job_id: str) -> bool:
        """Удаляет задание"""
        pass