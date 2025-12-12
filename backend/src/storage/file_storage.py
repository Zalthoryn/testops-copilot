# backend/src/storage/file_storage.py
"""
Хранилище файлов для TestOps Copilot
"""
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import UUID
import json
import zipfile
from datetime import datetime

from src.utils.logger import get_logger
from src.utils.exceptions import StorageException

logger = get_logger(__name__)


class FileStorage:
    """
    Управление файлами на файловой системе.
    
    Сохраняет сгенерированные тест-кейсы, автотесты и отчеты.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Инициализация файлового хранилища.
        
        Args:
            base_path: Базовый путь для хранения файлов
        """
        self.base_path = Path(base_path or os.getenv("STORAGE_PATH", "./storage"))
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Поддиректории
        self.jobs_path = self.base_path / "jobs"
        self.temp_path = self.base_path / "temp"
        self.exports_path = self.base_path / "exports"
        
        # Создаем директории
        for path in [self.jobs_path, self.temp_path, self.exports_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized FileStorage at {self.base_path.absolute()}")
    
    def create_job_directory(self, job_id: UUID) -> Path:
        """
        Создание директории для задания.
        
        Args:
            job_id: ID задания
        
        Returns:
            Путь к созданной директории
        """
        job_dir = self.jobs_path / str(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем поддиректории
        (job_dir / "testcases").mkdir(exist_ok=True)
        (job_dir / "autotests").mkdir(exist_ok=True)
        (job_dir / "reports").mkdir(exist_ok=True)
        
        logger.debug(f"Created job directory: {job_dir}")
        return job_dir
    
    def get_job_directory(self, job_id: UUID) -> Path:
        """
        Получение директории задания.
        
        Args:
            job_id: ID задания
        
        Returns:
            Путь к директории задания
        
        Raises:
            StorageException: Если директория не существует
        """
        job_dir = self.jobs_path / str(job_id)
        if not job_dir.exists():
            raise StorageException(f"Job directory not found: {job_id}")
        return job_dir
    
    def save_testcase_file(
        self,
        job_id: UUID,
        testcase_id: UUID,
        content: str,
        filename: Optional[str] = None
    ) -> Path:
        """
        Сохранение файла тест-кейса.
        
        Args:
            job_id: ID задания
            testcase_id: ID тест-кейса
            content: Содержимое файла
            filename: Имя файла (опционально)
        
        Returns:
            Путь к сохраненному файлу
        """
        try:
            job_dir = self.get_job_directory(job_id)
            testcases_dir = job_dir / "testcases"
            
            # Генерируем имя файла если не предоставлено
            if not filename:
                filename = f"testcase_{testcase_id}.py"
            
            filepath = testcases_dir / filename
            
            # Сохраняем файл
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Saved testcase file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving testcase file for job {job_id}: {e}")
            raise StorageException(f"Ошибка сохранения файла тест-кейса: {e}")
    
    def save_test_file(
        self,
        job_id: UUID,
        filename: str,
        content: str
    ) -> Path:
        """
        Сохранение файла автотеста.
        
        Args:
            job_id: ID задания
            filename: Имя файла
            content: Содержимое файла
        
        Returns:
            Путь к сохраненному файлу
        """
        try:
            job_dir = self.get_job_directory(job_id)
            autotests_dir = job_dir / "autotests"
            
            filepath = autotests_dir / filename
            
            # Сохраняем файл
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Saved test file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving test file for job {job_id}: {e}")
            raise StorageException(f"Ошибка сохранения файла автотеста: {e}")
    
    def save_json_file(
        self,
        job_id: UUID,
        filename: str,
        content: Dict[str, Any]
    ) -> Path:
        """
        Сохранение JSON файла.
        
        Args:
            job_id: ID задания
            filename: Имя файла
            content: Содержимое JSON
        
        Returns:
            Путь к сохраненному файлу
        """
        try:
            job_dir = self.get_job_directory(job_id)
            reports_dir = job_dir / "reports"
            
            filepath = reports_dir / filename
            
            # Сохраняем файл
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Saved JSON file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving JSON file for job {job_id}: {e}")
            raise StorageException(f"Ошибка сохранения JSON файла: {e}")
    
    def list_testcase_files(self, job_id: UUID) -> List[Path]:
        """
        Получение списка файлов тест-кейсов задания.
        
        Args:
            job_id: ID задания
        
        Returns:
            Список путей к файлам тест-кейсов
        """
        try:
            job_dir = self.get_job_directory(job_id)
            testcases_dir = job_dir / "testcases"
            
            if not testcases_dir.exists():
                return []
            
            return list(testcases_dir.glob("*.py"))
            
        except Exception as e:
            logger.error(f"Error listing testcase files for job {job_id}: {e}")
            raise StorageException(f"Ошибка получения списка файлов тест-кейсов: {e}")
    
    def list_test_files(self, job_id: UUID) -> List[Path]:
        """
        Получение списка файлов автотестов задания.
        
        Args:
            job_id: ID задания
        
        Returns:
            Список путей к файлам автотестов
        """
        try:
            job_dir = self.get_job_directory(job_id)
            autotests_dir = job_dir / "autotests"
            
            if not autotests_dir.exists():
                return []
            
            return list(autotests_dir.glob("*.py"))
            
        except Exception as e:
            logger.error(f"Error listing test files for job {job_id}: {e}")
            raise StorageException(f"Ошибка получения списка файлов автотестов: {e}")
    
    def create_zip_archive(
        self,
        job_id: UUID,
        prefix: str = "testcases"
    ) -> Path:
        """
        Создание ZIP архива с файлами задания.
        
        Args:
            job_id: ID задания
            prefix: Префикс для имени архива
        
        Returns:
            Путь к созданному архиву
        """
        try:
            job_dir = self.get_job_directory(job_id)
            
            # Определяем директорию для архивации
            source_dir = None
            if prefix == "testcases":
                source_dir = job_dir / "testcases"
            elif prefix == "autotests":
                source_dir = job_dir / "autotests"
            else:
                source_dir = job_dir
            
            if not source_dir.exists() or not any(source_dir.iterdir()):
                raise StorageException(f"No files found for archiving in {source_dir}")
            
            # Создаем архив
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{prefix}_{job_id}_{timestamp}.zip"
            archive_path = self.exports_path / archive_name
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        # Сохраняем относительный путь в архиве
                        arcname = file_path.relative_to(source_dir)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Created ZIP archive: {archive_path} ({source_dir.name})")
            return archive_path
            
        except StorageException:
            raise
        except Exception as e:
            logger.error(f"Error creating ZIP archive for job {job_id}: {e}")
            raise StorageException(f"Ошибка создания ZIP архива: {e}")
    
    def get_file_content(self, filepath: Path) -> str:
        """
        Получение содержимого файла.
        
        Args:
            filepath: Путь к файлу
        
        Returns:
            Содержимое файла
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            raise StorageException(f"Ошибка чтения файла: {e}")
    
    def delete_job_files(self, job_id: UUID) -> bool:
        """
        Удаление файлов задания.
        
        Args:
            job_id: ID задания
        
        Returns:
            True если файлы успешно удалены
        """
        try:
            job_dir = self.jobs_path / str(job_id)
            if job_dir.exists():
                shutil.rmtree(job_dir)
                logger.info(f"Deleted job files: {job_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting job files {job_id}: {e}")
            raise StorageException(f"Ошибка удаления файлов задания: {e}")
    
    def cleanup_old_files(self, days_old: int = 7) -> int:
        """
        Очистка старых файлов.
        
        Args:
            days_old: Возраст файлов в днях для удаления
        
        Returns:
            Количество удаленных директорий
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.now().timestamp() - (days_old * 86400)
            
            for job_dir in self.jobs_path.iterdir():
                if job_dir.is_dir():
                    try:
                        # Проверяем время последнего изменения
                        mtime = job_dir.stat().st_mtime
                        if mtime < cutoff_time:
                            shutil.rmtree(job_dir)
                            deleted_count += 1
                            logger.debug(f"Deleted old job directory: {job_dir.name}")
                    except Exception as e:
                        logger.warning(f"Error deleting old job directory {job_dir.name}: {e}")
                        continue
            
            # Очищаем старые архивы
            for archive in self.exports_path.glob("*.zip"):
                try:
                    mtime = archive.stat().st_mtime
                    if mtime < cutoff_time:
                        archive.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old archive: {archive.name}")
                except Exception as e:
                    logger.warning(f"Error deleting old archive {archive.name}: {e}")
                    continue
            
            logger.info(f"Cleaned up {deleted_count} old files")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")
            raise StorageException(f"Ошибка очистки старых файлов: {e}")
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики хранилища.
        
        Returns:
            Статистика использования хранилища
        """
        try:
            total_size = 0
            job_count = 0
            file_count = 0
            
            # Подсчитываем размер и количество файлов
            for job_dir in self.jobs_path.iterdir():
                if job_dir.is_dir():
                    job_count += 1
                    for file_path in job_dir.rglob("*"):
                        if file_path.is_file():
                            file_count += 1
                            total_size += file_path.stat().st_size
            
            # Подсчитываем архивы
            archive_count = len(list(self.exports_path.glob("*.zip")))
            for archive in self.exports_path.glob("*.zip"):
                total_size += archive.stat().st_size
            
            return {
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024),
                "job_count": job_count,
                "file_count": file_count,
                "archive_count": archive_count,
                "storage_path": str(self.base_path.absolute())
            }
            
        except Exception as e:
            logger.error(f"Error getting storage statistics: {e}")
            return {
                "error": str(e),
                "storage_path": str(self.base_path.absolute())
            }


def get_file_storage() -> FileStorage:
    """
    Фабрика для получения экземпляра FileStorage.
    
    Returns:
        Экземпляр FileStorage
    """
    return FileStorage()