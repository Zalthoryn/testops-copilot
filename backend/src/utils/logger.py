# backend/src/utils/logger.py
"""
Настройка логгера для TestOps Copilot
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Форматтер для вывода логов в JSON формате"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'job_id'):
            log_data["job_id"] = record.job_id
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Получение настроенного логгера.
    
    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Не настраиваем логгер повторно если уже настроен
    if logger.handlers:
        return logger
    
    # Устанавливаем уровень логирования
    log_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Создаем консольный handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Форматтер для консоли
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # Создаем файловый handler с ротацией
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "testops.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # JSON форматтер для файлов
    json_formatter = JSONFormatter()
    file_handler.setFormatter(json_formatter)
    
    # Добавляем handlers к логгеру
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    # Предотвращаем передачу логов корневому логгеру
    logger.propagate = False
    
    return logger


def setup_logging(level: str = "INFO"):
    """
    Настройка корневого логирования.
    
    Args:
        level: Уровень логирования
    """
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Удаляем существующие handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Добавляем консольный handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    root_logger.addHandler(console_handler)
    
    # Настраиваем логгеры для сторонних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


# Декоратор для логирования вызовов функций
def log_call(logger_name: str = None):
    """
    Декоратор для логирования вызовов функций.
    
    Args:
        logger_name: Имя логгера (если None, используется имя модуля)
    """
    def decorator(func):
        nonlocal logger_name
        if logger_name is None:
            logger_name = func.__module__
        
        logger = get_logger(logger_name)
        
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func.__name__} returned: {result}")
                return result
            except Exception as e:
                logger.error(f"{func.__name__} raised {type(e).__name__}: {e}", exc_info=True)
                raise
        
        # Сохраняем оригинальное имя функции
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        return wrapper
    
    return decorator