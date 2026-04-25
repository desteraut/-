"""
domain/entities/job.py
Сущность задания перевода (Translation Job)
Clean Architecture - Domain Layer
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class JobStatus(Enum):
    """Статусы задания перевода"""
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TranslationJob:
    """
    Сущность задания перевода
    
    Согласно PDF "Решение ключевых проблем локализации в Ren'Py":
    - Каждое задание имеет уникальный ID
    - Статус отслеживается через FSM
    - Кэш хранит metadata для инвалидации
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_text: str = ""
    translated_text: str = ""
    source_lang: str = "en"
    target_lang: str = "russian"
    file_path: str = ""
    line_number: int = 0
    status: JobStatus = JobStatus.PENDING
    error_message: Optional[str] = None
    engine_used: Optional[str] = None
    placeholders: Dict[str, str] = field(default_factory=dict)
    qa_result: Optional[Dict[str, Any]] = None
    cache_hit: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    retry_count: int = 0
    glossary_version: str = ""
    engine_model_version: str = ""
    
    def __post_init__(self):
        """Валидация после инициализации"""
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def start_processing(self) -> None:
        """Переводит задание в статус PROCESSING"""
        if self.status != JobStatus.PENDING:
            raise ValueError(f"Cannot start job in status {self.status.value}")
        self.status = JobStatus.PROCESSING
        self.started_at = datetime.now()
    
    def complete(self, translated_text: str, engine_name: str) -> None:
        """Завершает задание успешно"""
        self.translated_text = translated_text
        self.engine_used = engine_name
        self.status = JobStatus.DONE
        self.finished_at = datetime.now()
    
    def fail(self, error_message: str) -> None:
        """Отмечает задание как неудачное"""
        self.error_message = error_message
        self.status = JobStatus.FAILED
        self.finished_at = datetime.now()
    
    def cancel(self) -> None:
        """Отменяет задание"""
        if self.status in (JobStatus.DONE, JobStatus.FAILED):
            raise ValueError(f"Cannot cancel job in status {self.status.value}")
        self.status = JobStatus.CANCELLED
        self.finished_at = datetime.now()
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """Проверяет, можно ли повторить задание"""
        return self.status == JobStatus.FAILED and self.retry_count < max_retries
    
    def increment_retry(self) -> None:
        """Увеличивает счётчик попыток"""
        self.retry_count += 1
        self.status = JobStatus.PENDING
        self.error_message = None
        self.started_at = None
        self.finished_at = None
    
    def generate_cache_key(self) -> str:
        """
        Генерирует детерминированный ключ кэша с учётом версий
        
        Согласно PDF "Решение ключевых проблем локализации в Ren'Py":
        Ключ должен включать:
        - Текст
        - Версию глоссария
        - Версию модели движка
        - Языковую пару
        """
        import hashlib
        key_data = f"{self.original_text}|{self.source_lang}|{self.target_lang}|{self.glossary_version}|{self.engine_model_version}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Сериализует задание в словарь"""
        return {
            'id': self.id,
            'original_text': self.original_text,
            'translated_text': self.translated_text,
            'source_lang': self.source_lang,
            'target_lang': self.target_lang,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'status': self.status.value,
            'error_message': self.error_message,
            'engine_used': self.engine_used,
            'placeholders': self.placeholders,
            'qa_result': self.qa_result,
            'cache_hit': self.cache_hit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'retry_count': self.retry_count,
            'glossary_version': self.glossary_version,
            'engine_model_version': self.engine_model_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TranslationJob':
        """Десериализует задание из словаря"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            original_text=data.get('original_text', ''),
            translated_text=data.get('translated_text', ''),
            source_lang=data.get('source_lang', 'en'),
            target_lang=data.get('target_lang', 'russian'),
            file_path=data.get('file_path', ''),
            line_number=data.get('line_number', 0),
            status=JobStatus(data.get('status', 'pending')),
            error_message=data.get('error_message'),
            engine_used=data.get('engine_used'),
            placeholders=data.get('placeholders', {}),
            qa_result=data.get('qa_result'),
            cache_hit=data.get('cache_hit', False),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            finished_at=datetime.fromisoformat(data['finished_at']) if data.get('finished_at') else None,
            retry_count=data.get('retry_count', 0),
            glossary_version=data.get('glossary_version', ''),
            engine_model_version=data.get('engine_model_version', '')
        )