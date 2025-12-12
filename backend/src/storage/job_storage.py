"""
In-memory хранилище заданий для TestOps Copilot
Заменяет Redis на простое хранилище в памяти
"""
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from threading import Lock

from src.models.dto import JobResponse, JobStatus, TestCaseDTO
from src.utils.exceptions import JobNotFoundException
from src.utils.logger import get_logger

logger = get_logger(__name__)


class JobStorage:
    """
    In-memory хранилище для управления заданиями
    Thread-safe реализация без внешних зависимостей
    """

    def __init__(self):
        self._jobs: Dict[str, JobResponse] = {}
        self._lock = Lock()
        logger.info("JobStorage initialized (in-memory)")

    async def connect(self):
        """Совместимость с предыдущим API (ничего не делает)"""
        pass

    async def disconnect(self):
        """Совместимость с предыдущим API (ничего не делает)"""
        pass

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
        job_id = uuid4()
        now = datetime.now()

        job = JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Job created",
            created_at=now,
            updated_at=now,
            testcases=[],
            download_url=None,
            metrics=metadata or {}
        )

        with self._lock:
            self._jobs[str(job_id)] = job

        logger.info(f"Created job: {job_id} with status: {job.status}")
        return job

    async def get_job(self, job_id: UUID) -> Optional[JobResponse]:
        """
        Получение задания по ID

        Args:
            job_id: ID задания

        Returns:
            Объект задания или None если не найдено
        """
        with self._lock:
            job = self._jobs.get(str(job_id))

        if not job:
            return None

        return job

    async def update_job(self, job_id: UUID, updates: Dict[str, Any]) -> Optional[JobResponse]:
        """
        Обновление задания

        Args:
            job_id: ID задания
            updates: Словарь с обновлениями

        Returns:
            Обновленный объект задания
        """
        with self._lock:
            job = self._jobs.get(str(job_id))
            if not job:
                raise JobNotFoundException(f"Job {job_id} not found")

            # Создаем копию и обновляем
            job_dict = job.model_dump()
            job_dict.update(updates)
            job_dict['updated_at'] = datetime.now()

            # Конвертируем обратно в JobResponse
            updated_job = JobResponse(**job_dict)
            self._jobs[str(job_id)] = updated_job

        logger.info(f"Updated job: {job_id} with updates: {list(updates.keys())}")
        return updated_job

    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        message: Optional[str] = None
    ) -> Optional[JobResponse]:
        """
        Обновление статуса задания

        Args:
            job_id: ID задания
            status: Новый статус
            message: Сообщение

        Returns:
            Обновленный объект задания
        """
        updates = {"status": status}
        if message:
            updates["message"] = message

        return await self.update_job(job_id, updates)

    async def add_testcases_to_job(
        self,
        job_id: UUID,
        testcases: List[TestCaseDTO]
    ) -> Optional[JobResponse]:
        """
        Добавление тест-кейсов к заданию

        Args:
            job_id: ID задания
            testcases: Список тест-кейсов

        Returns:
            Обновленный объект задания
        """
        # Конвертируем тест-кейсы в словари для сериализации
        testcases_data = [tc.model_dump() if hasattr(tc, 'model_dump') else tc.dict() for tc in testcases]

        return await self.update_job(job_id, {"testcases": testcases_data})

    async def find_testcases_by_ids(self, testcase_ids: List[UUID]) -> List[TestCaseDTO]:
        """
        Find stored test cases by their IDs across all jobs.
        """
        if not testcase_ids:
            return []

        targets = {str(tc_id) for tc_id in testcase_ids}
        found: List[TestCaseDTO] = []

        with self._lock:
            for job in self._jobs.values():
                for tc in job.testcases or []:
                    tc_data = tc if isinstance(tc, dict) else tc.dict()
                    if str(tc_data.get("id")) in targets:
                        try:
                            found.append(TestCaseDTO(**tc_data))
                        except Exception:
                            continue

        return found

    async def delete_job(self, job_id: UUID) -> bool:
        """
        Удаление задания

        Args:
            job_id: ID задания

        Returns:
            True если удалено успешно
        """
        with self._lock:
            if str(job_id) in self._jobs:
                del self._jobs[str(job_id)]
                logger.info(f"Deleted job: {job_id}")
                return True

        return False

    async def list_jobs(
        self,
        status: Optional[JobStatus] = None,
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
        with self._lock:
            jobs = list(self._jobs.values())

        # Применяем фильтр по статусу
        if status:
            jobs = [j for j in jobs if j.status == status]

        # Сортируем по дате создания (новые первыми)
        jobs.sort(key=lambda x: x.created_at, reverse=True)

        # Применяем пагинацию
        return jobs[offset:offset + limit]

    async def get_recent_jobs(self, hours: int = 24) -> List[JobResponse]:
        """
        Получение недавних заданий

        Args:
            hours: Количество часов для фильтрации

        Returns:
            Список недавних заданий
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self._lock:
            jobs = [
                j for j in self._jobs.values()
                if j.created_at >= cutoff_time
            ]

        return sorted(jobs, key=lambda x: x.created_at, reverse=True)

    async def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Очистка старых заданий

        Args:
            days: Удалять задания старше N дней

        Returns:
            Количество удаленных заданий
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0

        with self._lock:
            to_delete = [
                job_id for job_id, job in self._jobs.items()
                if job.created_at < cutoff_time
            ]

            for job_id in to_delete:
                del self._jobs[job_id]
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} jobs older than {days} days")
        return deleted_count

    async def get_job_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики по заданиям

        Returns:
            Словарь со статистикой
        """
        with self._lock:
            jobs = list(self._jobs.values())

        status_counts = {
            JobStatus.PENDING: 0,
            JobStatus.PROCESSING: 0,
            JobStatus.COMPLETED: 0,
            JobStatus.FAILED: 0
        }

        total_testcases = 0

        for job in jobs:
            if job.status in status_counts:
                status_counts[job.status] += 1

            if job.testcases:
                total_testcases += len(job.testcases)

        total_jobs = len(jobs)
        status_percentages = {}
        if total_jobs > 0:
            for status, count in status_counts.items():
                status_percentages[status.value] = round((count / total_jobs) * 100, 1)

        return {
            "total_jobs": total_jobs,
            "status_counts": {k.value: v for k, v in status_counts.items()},
            "status_percentages": status_percentages,
            "total_testcases": total_testcases,
            "average_testcases_per_job": round(total_testcases / total_jobs, 1) if total_jobs > 0 else 0
        }


# Глобальный экземпляр хранилища
_job_storage_instance: Optional[JobStorage] = None


def get_job_storage() -> JobStorage:
    """
    Получение глобального экземпляра JobStorage (singleton)

    Returns:
        Экземпляр JobStorage
    """
    global _job_storage_instance
    if _job_storage_instance is None:
        _job_storage_instance = JobStorage()
    return _job_storage_instance
