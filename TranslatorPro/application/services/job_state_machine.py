"""
application/services/job_state_machine.py
State Machine для управления жизненным циклом заданий
ИСПРАВЛЕНО: Атомарные переходы, rollback при ошибках
Согласно PDF "Решение ключевых проблем локализации в Ren'Py"
"""
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import logging

# ✅ ИСПРАВЛЕНО: __name__ вместо name
logger = logging.getLogger(__name__)

from domain.entities.job import TranslationJob, JobStatus
from ports.storage_port import StoragePort

class TransitionError(Exception):
    """Исключение для недопустимых переходов состояния"""
    pass

class JobStateMachine:
    """
    FSM для управления жизненным циклом задания перевода
    Ключевые особенности:
    - Валидация переходов
    - Атомарное сохранение
    - Rollback при ошибках
    - Поддержка retry
    """
    
    # Допустимые переходы: current_status -> [allowed_next_statuses]
    ALLOWED_TRANSITIONS = {
        JobStatus.PENDING: [JobStatus.PROCESSING, JobStatus.CANCELLED],
        JobStatus.PROCESSING: [JobStatus.DONE, JobStatus.FAILED],
        JobStatus.DONE: [],
        JobStatus.FAILED: [JobStatus.PENDING],  # retry
        JobStatus.CANCELLED: [],
    }

    def __init__(self, storage: StoragePort, max_retries: int = 3):
        self._storage = storage
        self._max_retries = max_retries

    def transition(self, job: TranslationJob, new_status: JobStatus) -> bool:
        """
        Атомарный переход состояния с валидацией
        
        Args:
            job: Задание для перехода
            new_status: Новое состояние
            
        Returns:
            True если переход успешен
            
        Raises:
            TransitionError: Если переход недопустим
        """
        current = job.status
        
        # Валидация перехода
        if new_status not in self.ALLOWED_TRANSITIONS.get(current, []):
            raise TransitionError(
                f"Invalid transition: {current.value} -> {new_status.value}"
            )
        
        # Обновление временных меток
        now = datetime.now()
        if new_status == JobStatus.PROCESSING:
            job.started_at = now
        elif new_status in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED):
            job.finished_at = now
        
        job.status = new_status
        
        # Атомарное сохранение
        success = self._storage.update_job(job)
        
        if success:
            logger.debug(f"🔄 Job {job.id[:8]}... transition: {current.value} -> {new_status.value}")
        else:
            logger.error(f"❌ Job {job.id[:8]}... transition failed: {current.value} -> {new_status.value}")
        
        return success

    def process_with_rollback(
        self,
        job_id: str,
        operation: Callable[[], str]
    ) -> bool:
        """
        Выполняет операцию с автоматическим rollback на FAILED при ошибке
        
        Pattern: Transaction Script с компенсацией
        
        Args:
            job_id: ID задания
            operation: Функция перевода (возвращает translated_text)
            
        Returns:
            True если успешно
        """
        job = self._storage.get_job(job_id)
        if not job:
            logger.error(f"❌ Job {job_id} not found")
            return False
        
        try:
            # Переход в PROCESSING
            self.transition(job, JobStatus.PROCESSING)
            
            # Выполнение операции
            translated_text = operation()
            
            # Переход в DONE
            job.complete(translated_text, job.engine_used or "unknown")
            self.transition(job, JobStatus.DONE)
            
            logger.info(f"✅ Job {job_id[:8]}... completed successfully")
            return True
            
        except Exception as e:
            logger.exception(f"❌ Job {job_id[:8]}... failed: {e}")
            
            # Rollback на FAILED
            job.fail(str(e))
            self.transition(job, JobStatus.FAILED)
            
            return False

    def retry_job(self, job_id: str) -> bool:
        """
        Повторяет неудачное задание
        
        Args:
            job_id: ID задания
            
        Returns:
            True если retry возможен
        """
        job = self._storage.get_job(job_id)
        if not job:
            logger.error(f"❌ Job {job_id} not found")
            return False
        
        if not job.can_retry(self._max_retries):
            logger.warning(f"⚠️ Job {job_id[:8]}... cannot retry (max retries reached)")
            return False
        
        job.increment_retry()
        self.transition(job, JobStatus.PENDING)
        
        logger.info(f"🔄 Job {job_id[:8]}... retry #{job.retry_count}")
        return True

    def cancel_job(self, job_id: str) -> bool:
        """
        Отменяет задание
        
        Args:
            job_id: ID задания
            
        Returns:
            True если отмена успешна
        """
        job = self._storage.get_job(job_id)
        if not job:
            logger.error(f"❌ Job {job_id} not found")
            return False
        
        try:
            self.transition(job, JobStatus.CANCELLED)
            logger.info(f"🚫 Job {job_id[:8]}... cancelled")
            return True
        except TransitionError as e:
            logger.warning(f"⚠️ Job {job_id[:8]}... cannot cancel: {e}")
            return False

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает статус задания
        
        Args:
            job_id: ID задания
            
        Returns:
            Dict со статусом или None
        """
        job = self._storage.get_job(job_id)
        if not job:
            return None
        
        return {
            'id': job.id,
            'status': job.status.value,
            'original_text': job.original_text[:50] + '...' if len(job.original_text) > 50 else job.original_text,
            'translated_text': job.translated_text[:50] + '...' if job.translated_text and len(job.translated_text) > 50 else job.translated_text,
            'error_message': job.error_message,
            'retry_count': job.retry_count,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'finished_at': job.finished_at.isoformat() if job.finished_at else None
        }