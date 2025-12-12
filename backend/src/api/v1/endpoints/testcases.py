"""
API endpoints for manual test case generation.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse

from src.models.dto import (
    JobResponse,
    JobStatusResponse,
    ManualAPIGenerationRequest,
    ManualUIGenerationRequest,
    TestCaseDTO,
)
from src.models.enums import JobStatus
from src.services.job_manager import JobManager, get_job_manager
from src.services.llm_client import LLMClient, get_llm_client
from src.agents.requirements_to_manual_tc import (
    RequirementsToManualTCAgent,
    RequirementsToManualTCInput,
)
from src.agents.openapi_to_api_tc import (
    OpenAPIToAPITCAgent,
    OpenAPIToAPITCInput,
)
from src.storage.file_storage import FileStorage, get_file_storage
from src.utils.logger import get_logger
from src.utils.exceptions import TestOpsException

router = APIRouter(prefix="/testcases", tags=["testcases"])
logger = get_logger(__name__)


@router.post("/manual/ui", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_manual_ui_testcases(
    request: ManualUIGenerationRequest,
    background_tasks: BackgroundTasks,
    llm_client: LLMClient = Depends(get_llm_client),
    job_manager: JobManager = Depends(get_job_manager),
    file_storage: FileStorage = Depends(get_file_storage),
) -> JobResponse:
    """Generate manual UI test cases using LLM."""
    try:
        agent = RequirementsToManualTCAgent(llm_client)
        agent_input = RequirementsToManualTCInput(job_id=UUID(int=0), **request.dict())

        job = await job_manager.create_job(
            job_type="manual_ui_generation",
            metadata={"project": request.project_name},
        )
        agent_input.job_id = job.job_id
        await job_manager.update_job_status(job.job_id, JobStatus.PROCESSING, "Generation started")

        file_storage.create_job_directory(job.job_id)
        background_tasks.add_task(
            process_ui_generation_results,
            job.job_id,
            agent,
            agent_input,
            job_manager,
            file_storage,
        )

        return await job_manager.get_job_status(job.job_id) or job

    except TestOpsException as exc:
        logger.error(f"TestOps error in UI generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in UI generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        )


@router.post("/manual/api", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_manual_api_testcases(
    request: ManualAPIGenerationRequest,
    background_tasks: BackgroundTasks,
    llm_client: LLMClient = Depends(get_llm_client),
    job_manager: JobManager = Depends(get_job_manager),
    file_storage: FileStorage = Depends(get_file_storage),
) -> JobResponse:
    """Generate manual API test cases from OpenAPI."""
    try:
        agent = OpenAPIToAPITCAgent(llm_client)
        agent_input = OpenAPIToAPITCInput(job_id=UUID(int=0), **request.dict())

        job = await job_manager.create_job(
            job_type="manual_api_generation",
            metadata={"sections": request.sections},
        )
        agent_input.job_id = job.job_id
        await job_manager.update_job_status(job.job_id, JobStatus.PROCESSING, "Generation started")

        file_storage.create_job_directory(job.job_id)
        background_tasks.add_task(
            process_api_generation_results,
            job.job_id,
            agent,
            agent_input,
            job_manager,
            file_storage,
        )

        return await job_manager.get_job_status(job.job_id) or job

    except TestOpsException as exc:
        logger.error(f"TestOps error in API generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in API generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_testcase_generation_status(
    job_id: UUID,
    job_manager: JobManager = Depends(get_job_manager),
) -> JobStatusResponse:
    """Get status of a generation job."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    if job.status == JobStatus.COMPLETED:
        job.download_url = f"/api/v1/testcases/{job_id}/download"
    return job


@router.get("/{job_id}/download")
async def download_testcases(
    job_id: UUID,
    file_storage: FileStorage = Depends(get_file_storage),
) -> FileResponse:
    """Download generated testcases as zip."""
    archive_path = file_storage.create_zip_archive(job_id)
    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No test cases found for job {job_id}",
        )

    return FileResponse(
        path=archive_path,
        filename=f"testcases_{job_id}.zip",
        media_type="application/zip",
    )


@router.get("/", response_model=List[JobResponse])
async def list_testcase_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    job_manager: JobManager = Depends(get_job_manager),
) -> List[JobResponse]:
    """List generation jobs."""
    job_status = None
    if status:
        try:
            job_status = JobStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value",
            )

    return await job_manager.job_storage.list_jobs(
        status=job_status, limit=limit, offset=offset
    )


async def process_ui_generation_results(
    job_id: UUID,
    agent: RequirementsToManualTCAgent,
    agent_input: RequirementsToManualTCInput,
    job_manager: JobManager,
    file_storage: FileStorage,
):
    """Run UI generation and persist results."""
    try:
        agent_input.job_id = job_id
        result = await agent.execute(agent_input)

        if result.success and result.testcases:
            for testcase in result.testcases:
                file_storage.save_testcase_file(
                    job_id=job_id,
                    testcase_id=testcase.id,
                    content=testcase.python_code,
                    filename=f"testcase_{testcase.id}.py",
                )
            await job_manager.job_storage.add_testcases_to_job(job_id, result.testcases)
            await job_manager.update_job_status(
                job_id, JobStatus.COMPLETED, "UI test cases generated successfully"
            )
        else:
            await job_manager.update_job_status(
                job_id, JobStatus.FAILED, f"UI generation failed: {result.error}"
            )
    except Exception as exc:
        logger.error(f"Error processing UI results for job {job_id}: {exc}")
        await job_manager.update_job_status(
            job_id, JobStatus.FAILED, f"Error processing results: {exc}"
        )


async def process_api_generation_results(
    job_id: UUID,
    agent: OpenAPIToAPITCAgent,
    agent_input: OpenAPIToAPITCInput,
    job_manager: JobManager,
    file_storage: FileStorage,
):
    """Run API generation and persist results."""
    try:
        agent_input.job_id = job_id
        result = await agent.execute(agent_input)

        if result.success and result.testcases:
            for testcase in result.testcases:
                file_storage.save_testcase_file(
                    job_id=job_id,
                    testcase_id=testcase.id,
                    content=testcase.python_code,
                    filename=f"testcase_{testcase.id}.py",
                )
            await job_manager.job_storage.add_testcases_to_job(job_id, result.testcases)
            await job_manager.update_job_status(
                job_id, JobStatus.COMPLETED, "API test cases generated successfully"
            )
        else:
            await job_manager.update_job_status(
                job_id, JobStatus.FAILED, f"API generation failed: {result.error}"
            )
    except Exception as exc:
        logger.error(f"Error processing API results for job {job_id}: {exc}")
        await job_manager.update_job_status(
            job_id, JobStatus.FAILED, f"Error processing results: {exc}"
        )
