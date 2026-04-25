"""
Logger — система логирования с поддержкой файла и консоли
"""
import logging
from pathlib import Path
from typing import Optional

def setup_logger(name: str, log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Настраивает и возвращает logger
    
    Args:
        name: Имя логгера
        log_file: Путь к файлу логов (опционально)
        level: Уровень логирования
    
    Returns:
        Настроенный объект Logger
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    
    if logger.handlers:
        logger.handlers.clear()
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create log file {log_file}: {e}")
    
    return logger

def get_logger(name: str = __name__) -> logging.Logger:
    """Быстрое получение логгера с настройками по умолчанию"""
    try:
        from config import LOG_FILE
        return setup_logger(name, log_file=LOG_FILE)
    except ImportError:
        return setup_logger(name)