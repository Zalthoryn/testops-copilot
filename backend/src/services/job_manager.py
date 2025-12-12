"""
Менеджер заданий для обработки фоновых задач
"""
import asyncio
from typing import Dict, List, Optional, Any, Callable
from uuid import UUID
from concurrent.futures import ThreadPoolExecutor

from src.models.dto import JobResponse, JobStatus
from src.storage.job_storage import JobStorage, get_job_storage
from src.utils.logger import get_logger
from src.utils.exceptions import JobNotFoundException

logger = get_logger(__name__)


class JobManager:
    """Менеджер для управления фоновыми заданиями"""

    def __init__(
        self,
        job_storage: Optional[JobStorage] = None,
        max_workers: int = 10
    ):
        """
        Инициализация менеджера заданий

        Args:
            job_storage: Хранилище заданий (если None, используется глобальное)
            max_workers: Максимальное количество воркеров
        """
        self.job_storage = job_storage or get_job_storage()
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Словарь для отслеживания выполняемых задач
        self.running_tasks: Dict[UUID, asyncio.Task] = {}
        self.task_callbacks: Dict[UUID, List[Callable]] = {}

        logger.info(f"JobManager initialized with {max_workers} workers")

    async def create_job(
        self,
        job_type: str = "testcase_generation",
        metadata: Optional[Dict[str, Any]] = None
    ) -> JobResponse:
        """
        Создание нового задания

        Args:
            job_type: Тип задания
            metadata: Дополнительные метаданные

        Returns:
            Созданное задание
        """
        job = await self.job_storage.create_job(job_type=job_type, metadata=metadata)
        logger.info(f"Created new job: {job.job_id}")
        return job

    async def start_job(
        self,
        job_id: UUID,
        task_func: Callable,
        *args,
        **kwargs
    ) -> JobResponse:
        """
        Запуск задания на выполнение

        Args:
            job_id: ID задания
            task_func: Функция для выполнения
            *args: Аргументы функции
            **kwargs: Ключевые аргументы функции

        Returns:
            Объект задания
        """
        # Обновляем статус на PROCESSING
        job = await self.job_storage.update_job_status(
            job_id,
            JobStatus.PROCESSING,
            "Job started"
        )

        if not job:
            raise JobNotFoundException(f"Job {job_id} not found")

        # Создаем асинхронную задачу
        task = asyncio.create_task(
            self._execute_task(job_id, task_func, *args, **kwargs)
        )

        # Сохраняем задачу в словаре
        self.running_tasks[job_id] = task

        # Добавляем callback для очистки
        task.add_done_callback(lambda t: self._cleanup_task(job_id))

        logger.info(f"Started job {job_id}")
        return job

    async def submit_job(
        self,
        job_id: Optional[UUID],
        task_func: Callable,
        input_data: Any,
        *args,
        **kwargs
    ) -> JobResponse:
        """
        Convenience wrapper to create a job and start execution.
        The provided job_id is ignored; a fresh job id is generated.
        """
        job = await self.create_job(job_type=task_func.__name__)

        if hasattr(input_data, "job_id"):
            try:
                input_data.job_id = job.job_id
            except Exception:
                pass

        await self.start_job(job.job_id, task_func, input_data, *args, **kwargs)
        return job

    async def _execute_task(
        self,
        job_id: UUID,
        task_func: Callable,
        *args,
        **kwargs
    ):
        """
        Выполнение задачи

        Args:
            job_id: ID задания
            task_func: Функция для выполнения
        """
        try:
            logger.info(f"Executing job {job_id}")

            # Выполняем задачу
            if asyncio.iscoroutinefunction(task_func):
                result = await task_func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    lambda: task_func(*args, **kwargs)
                )

            # Обновляем статус на COMPLETED
            await self.job_storage.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                "Job completed successfully"
            )

            # Вызываем колбэки
            await self._call_callbacks(job_id, result, None)

            logger.info(f"Job {job_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")

            # Обновляем статус на FAILED
            await self.job_storage.update_job_status(
                job_id,
                JobStatus.FAILED,
                f"Job failed: {str(e)}"
            )

            # Вызываем колбэки с ошибкой
            await self._call_callbacks(job_id, None, e)
            raise

    async def _call_callbacks(self, job_id: UUID, result: Any, error: Optional[Exception]):
        """Вызов колбэков для задания"""
        if job_id in self.task_callbacks:
            for callback in self.task_callbacks[job_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(job_id, result, error)
                    else:
                        callback(job_id, result, error)
                except Exception as e:
                    logger.error(f"Callback error for job {job_id}: {e}")

    def _cleanup_task(self, job_id: UUID):
        """Очистка завершенной задачи"""
        if job_id in self.running_tasks:
            del self.running_tasks[job_id]

        if job_id in self.task_callbacks:
            del self.task_callbacks[job_id]

        logger.debug(f"Cleaned up task for job {job_id}")

    async def get_job_status(self, job_id: UUID) -> Optional[JobResponse]:
        """
        Получение статуса задания

        Args:
            job_id: ID задания

        Returns:
            Объект задания или None
        """
        return await self.job_storage.get_job(job_id)

    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        message: Optional[str] = None
    ) -> Optional[JobResponse]:
        """
        Обновление статуса задания

        Args:
            job_id: ID задания
            status: Новый статус (строка)
            message: Сообщение

        Returns:
            Обновленный объект задания
        """
        # Конвертируем строку в enum
        if isinstance(status, str):
            status = JobStatus(status.lower())

        return await self.job_storage.update_job_status(job_id, status, message)

    async def add_testcases_to_job(
        self,
        job_id: UUID,
        testcases: List[Any]
    ) -> Optional[JobResponse]:
        """
        Добавление тест-кейсов к заданию

        Args:
            job_id: ID задания
            testcases: Список тест-кейсов

        Returns:
            Обновленный объект задания
        """
        return await self.job_storage.add_testcases_to_job(job_id, testcases)

    async def cancel_job(self, job_id: UUID) -> bool:
        """
        Отмена задания

        Args:
            job_id: ID задания

        Returns:
            True если отменено успешно
        """
        if job_id in self.running_tasks:
            task = self.running_tasks[job_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                logger.info(f"Job {job_id} cancelled")

            await self.job_storage.update_job_status(
                job_id,
                JobStatus.FAILED,
                "Job cancelled by user"
            )

            return True

        return False

    async def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[JobResponse]:
        """
        Получение списка заданий

        Args:
            status: Фильтр по статусу
            limit: Максимальное количество
            offset: Смещение

        Returns:
            Список заданий
        """
        status_enum = JobStatus(status.lower()) if status else None
        return await self.job_storage.list_jobs(status=status_enum, limit=limit, offset=offset)

    async def is_job_running(self, job_id: UUID) -> bool:
        """Проверка, выполняется ли задание"""
        return job_id in self.running_tasks

    async def get_running_jobs(self) -> List[UUID]:
        """Получение списка выполняющихся заданий"""
        return list(self.running_tasks.keys())

    def add_callback(self, job_id: UUID, callback: Callable):
        """Добавление колбэка для задания"""
        if job_id not in self.task_callbacks:
            self.task_callbacks[job_id] = []
        self.task_callbacks[job_id].append(callback)

    async def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики"""
        storage_stats = await self.job_storage.get_job_statistics()

        return {
            **storage_stats,
            "running_jobs": len(self.running_tasks),
            "max_workers": self.max_workers
        }

    async def shutdown(self):
        """Завершение работы менеджера"""
        logger.info("Shutting down JobManager")

        # Отменяем все выполняющиеся задачи
        for job_id, task in self.running_tasks.items():
            task.cancel()
            logger.info(f"Cancelled job {job_id}")

        # Ждем завершения
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        # Завершаем executor
        self.executor.shutdown(wait=True)

        logger.info("JobManager shutdown complete")


# Глобальный экземпляр
_job_manager_instance: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """
    Получение глобального экземпляра JobManager (singleton)

    Returns:
        Экземпляр JobManager
    """
    global _job_manager_instance
    if _job_manager_instance is None:
        _job_manager_instance = JobManager()
    return _job_manager_instance
