import logging
import time
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger('apps')


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                f'{func.__module__}.{func.__name__} completed',
                extra={
                    'function': f'{func.__module__}.{func.__name__}',
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'success',
                }
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f'{func.__module__}.{func.__name__} failed: {e}',
                extra={
                    'function': f'{func.__module__}.{func.__name__}',
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'error',
                    'error': str(e),
                },
                exc_info=True,
            )
            raise
    return wrapper


def log_celery_task(func: Callable) -> Callable:
    """Decorator to log Celery task execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        task_name = func.__name__
        start_time = time.time()
        logger.info(f'Celery task {task_name} started', extra={'task': task_name, 'status': 'started'})
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(
                f'Celery task {task_name} completed',
                extra={
                    'task': task_name,
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'success',
                }
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f'Celery task {task_name} failed: {e}',
                extra={
                    'task': task_name,
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'error',
                    'error': str(e),
                },
                exc_info=True,
            )
            raise
    return wrapper


class PerformanceMonitor:
    """Context manager for monitoring code block performance."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f'Starting {self.operation_name}')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        if exc_type is None:
            logger.info(
                f'{self.operation_name} completed',
                extra={
                    'operation': self.operation_name,
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'success',
                }
            )
        else:
            logger.error(
                f'{self.operation_name} failed: {exc_val}',
                extra={
                    'operation': self.operation_name,
                    'duration_ms': round(duration * 1000, 2),
                    'status': 'error',
                    'error': str(exc_val),
                },
                exc_info=True,
            )
        return False
