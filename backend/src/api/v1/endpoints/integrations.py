# backend/src/api/v1/endpoints/integrations.py
"""
API endpoints для интеграций с внешними системами (GitLab, Evolution Compute)
"""
from typing import Dict, Any, List
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status

from ....models.dto import GitLabCommitRequest
from ....services.job_manager import JobManager, get_job_manager
from ....services.gitlab_client import GitLabClient, get_gitlab_client
from ....services.compute_api_client import EvolutionComputeClient, get_compute_client
from ....storage.file_storage import FileStorage, get_file_storage
from ....utils.logger import get_logger
from ....utils.exceptions import TestOpsException

logger = get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/gitlab/commit", status_code=status.HTTP_202_ACCEPTED)
async def commit_to_gitlab(
    request: GitLabCommitRequest,
    background_tasks: BackgroundTasks,
    job_manager: JobManager = Depends(get_job_manager),
    gitlab_client: GitLabClient = Depends(get_gitlab_client),
    file_storage: FileStorage = Depends(get_file_storage)
) -> Dict[str, Any]:
    """
    Отправка тест-кейсов в GitLab
    
    - **testcases_job_id**: ID задания с тест-кейсами
    - **repository**: Репозиторий GitLab (owner/repo)
    - **branch**: Ветка для коммита
    - **commit_message**: Сообщение коммита
    - **create_mr**: Создать merge request
    """
    try:
        logger.info(f"Starting GitLab commit for job: {request.testcases_job_id}")
        
        # Получаем тест-кейсы из задания
        testcases = await job_manager.job_storage.get_job_testcases(request.testcases_job_id)
        
        if not testcases:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No testcases found for job {request.testcases_job_id}"
            )
        
        # Подготавливаем тест-кейсы для загрузки
        testcases_for_upload = []
        for testcase in testcases:
            # Генерируем имя файла на основе названия тест-кейса
            import re
            filename = re.sub(r'[^a-zA-Z0-9]', '_', testcase.title).lower() + '.py'
            filename = re.sub(r'_+', '_', filename).strip('_')
            
            testcases_for_upload.append({
                "id": testcase.id,
                "filename": f"test_{filename}",
                "python_code": testcase.python_code,
                "title": testcase.title
            })
        
        # Создаем задание для фоновой обработки
        job = await job_manager.submit_job(
            job_id=UUID(int=0),  # Временный ID
            task_func=_process_gitlab_commit,
            request=request,
            testcases=testcases_for_upload,
            gitlab_client=gitlab_client
        )
        
        # Добавляем задачу для обработки
        background_tasks.add_task(
            _execute_gitlab_commit,
            job.job_id,
            request,
            testcases_for_upload,
            job_manager,
            gitlab_client
        )
        
        return {
            "job_id": job.job_id,
            "status": "processing",
            "message": "GitLab commit started",
            "testcases_count": len(testcases_for_upload)
        }
        
    except HTTPException:
        raise
    except TestOpsException as e:
        logger.error(f"TestOps error in GitLab commit: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in GitLab commit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/gitlab/projects")
async def get_gitlab_projects(
    gitlab_client: GitLabClient = Depends(get_gitlab_client)
) -> List[Dict[str, Any]]:
    """
    Получение списка проектов GitLab
    
    Returns:
        Список проектов GitLab
    """
    try:
        logger.info("Getting GitLab projects")
        
        # TODO: Реализовать получение списка проектов через GitLab API
        # Временная заглушка
        return [
            {
                "id": "123456",
                "name": "Test Project",
                "path": "test/project",
                "web_url": "https://gitlab.com/test/project"
            }
        ]
        
    except TestOpsException as e:
        logger.error(f"TestOps error getting GitLab projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting GitLab projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/gitlab/branches/{project_id}")
async def get_gitlab_branches(
    project_id: str,
    gitlab_client: GitLabClient = Depends(get_gitlab_client)
) -> List[Dict[str, Any]]:
    """
    Получение списка веток проекта GitLab
    
    - **project_id**: ID проекта GitLab
    
    Returns:
        Список веток проекта
    """
    try:
        logger.info(f"Getting GitLab branches for project {project_id}")
        
        # TODO: Реализовать получение веток через GitLab API
        # Временная заглушка
        return [
            {
                "name": "main",
                "default": True,
                "protected": True
            },
            {
                "name": "develop",
                "default": False,
                "protected": False
            },
            {
                "name": "feature/test-automation",
                "default": False,
                "protected": False
            }
        ]
        
    except TestOpsException as e:
        logger.error(f"TestOps error getting GitLab branches: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error getting GitLab branches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/compute/test")
async def test_compute_operation(
    operation: str = "list_vms",
    compute_client: EvolutionComputeClient = Depends(get_compute_client)
) -> Dict[str, Any]:
    """
    Тестирование операции Evolution Compute API
    
    - **operation**: Операция для тестирования (list_vms, create_vm, etc.)
    
    Returns:
        Результат тестовой операции
    """
    try:
        logger.info(f"Testing Compute API operation: {operation}")
        
        if operation == "list_vms":
            vms = await compute_client.get_virtual_machines(limit=5)
            return {
                "operation": "list_vms",
                "success": True,
                "result": vms,
                "count": len(vms)
            }
        
        elif operation == "list_disks":
            disks = await compute_client.get_disks(limit=5)
            return {
                "operation": "list_disks",
                "success": True,
                "result": disks,
                "count": len(disks)
            }
        
        elif operation == "list_flavors":
            flavors = await compute_client.get_flavors(limit=5)
            return {
                "operation": "list_flavors",
                "success": True,
                "result": flavors,
                "count": len(flavors)
            }
        
        elif operation == "health_check":
            health = await compute_client.health_check()
            return {
                "operation": "health_check",
                "success": True,
                "result": health
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported operation: {operation}"
            )
        
    except TestOpsException as e:
        logger.error(f"TestOps error testing Compute operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error testing Compute operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# Вспомогательные функции
async def _process_gitlab_commit(
    request: GitLabCommitRequest,
    testcases: List[Dict[str, Any]],
    gitlab_client: GitLabClient
) -> Dict[str, Any]:
    """Обработка коммита в GitLab (для JobManager)"""
    try:
        # Загружаем тест-кейсы в GitLab
        result = await gitlab_client.upload_test_cases(
            test_cases=testcases,
            branch=request.branch,
            commit_message=request.commit_message,
            create_mr=request.create_mr,
            target_branch=request.target_branch,
            mr_title=request.mr_title,
            mr_description=request.mr_description
        )
        
        return {
            "success": True,
            "result": result,
            "testcases_count": len(testcases)
        }
        
    except Exception as e:
        logger.error(f"Error in GitLab commit processing: {e}")
        return {
            "success": False,
            "error": str(e),
            "testcases_count": len(testcases)
        }


async def _execute_gitlab_commit(
    job_id: UUID,
    request: GitLabCommitRequest,
    testcases: List[Dict[str, Any]],
    job_manager: JobManager,
    gitlab_client: GitLabClient
):
    """Выполнение коммита в GitLab в фоновом режиме"""
    try:
        logger.info(f"Executing GitLab commit for job: {job_id}")
        
        # Выполняем коммит
        result = await _process_gitlab_commit(request, testcases, gitlab_client)
        
        if result["success"]:
            await job_manager.update_job_status(
                job_id,
                "completed",
                f"Successfully committed {result['testcases_count']} test cases to GitLab"
            )
            logger.info(f"GitLab commit completed for job: {job_id}")
        else:
            await job_manager.update_job_status(
                job_id,
                "failed",
                f"GitLab commit failed: {result['error']}"
            )
            logger.error(f"GitLab commit failed for job {job_id}: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error executing GitLab commit for job {job_id}: {e}")
        await job_manager.update_job_status(
            job_id,
            "failed",
            f"Error executing GitLab commit: {str(e)}"
        )