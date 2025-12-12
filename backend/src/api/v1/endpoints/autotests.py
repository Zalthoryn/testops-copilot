"""
API endpoints for autotest generation.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse

from src.models.dto import (
    APIAutotestsRequest,
    JobResponse,
    JobStatusResponse,
    TestCaseDTO,
    UIAutotestsRequest,
)
from src.models.enums import JobStatus
from src.services.job_manager import JobManager, get_job_manager
from src.services.llm_client import LLMClient, get_llm_client
from src.agents.manual_to_ui_tests import ManualToUITestsAgent, ManualToUITestsInput
from src.agents.openapi_to_api_tests import (
    OpenAPIToAPITestsAgent,
    OpenAPIToAPITestsInput,
)
from src.storage.file_storage import FileStorage, get_file_storage
from src.utils.logger import get_logger
from src.utils.exceptions import TestOpsException

router = APIRouter(prefix="/autotests", tags=["autotests"])
logger = get_logger(__name__)


@router.post("/ui", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_ui_autotests(
    request: UIAutotestsRequest,
    background_tasks: BackgroundTasks,
    llm_client: LLMClient = Depends(get_llm_client),
    job_manager: JobManager = Depends(get_job_manager),
    file_storage: FileStorage = Depends(get_file_storage),
) -> JobResponse:
    """Generate UI autotests from manual test cases."""
    try:
        testcases = await job_manager.job_storage.find_testcases_by_ids(
            request.manual_testcases_ids
        )
        if not testcases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No manual testcases found for provided IDs",
            )

        agent = ManualToUITestsAgent(llm_client)
        agent_input = ManualToUITestsInput(
            job_id=UUID(int=0),
            testcases=testcases,
            framework=request.framework or "playwright",
            browsers=request.browsers or ["chromium"],
            base_url=request.base_url or "https://cloud.ru/calculator",
            headless=request.headless,
            priority_filter=request.priority_filter,
        )

        job = await job_manager.create_job(
            job_type="ui_autotests", metadata={"framework": agent_input.framework}
        )
        agent_input.job_id = job.job_id
        await job_manager.update_job_status(
            job.job_id, JobStatus.PROCESSING, "Autotest generation started"
        )

        file_storage.create_job_directory(job.job_id)
        background_tasks.add_task(
            process_ui_autotest_results,
            job.job_id,
            agent,
            agent_input,
            job_manager,
            file_storage,
        )

        return await job_manager.get_job_status(job.job_id) or job

    except HTTPException:
        raise
    except TestOpsException as exc:
        logger.error(f"TestOps error in UI autotest generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in UI autotest generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        )


@router.post("/api", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_api_autotests(
    request: APIAutotestsRequest,
    background_tasks: BackgroundTasks,
    llm_client: LLMClient = Depends(get_llm_client),
    job_manager: JobManager = Depends(get_job_manager),
    file_storage: FileStorage = Depends(get_file_storage),
) -> JobResponse:
    """Generate API autotests from OpenAPI."""
    try:
        agent = OpenAPIToAPITestsAgent(llm_client)
        agent_input = OpenAPIToAPITestsInput(
            job_id=UUID(int=0),
            openapi_url=request.openapi_url,
            sections=request.sections,
            base_url=request.base_url,
            auth_token=request.auth_token,
            test_framework=request.test_framework,
            http_client=request.http_client,
            target_count=10,
        )

        job = await job_manager.create_job(
            job_type="api_autotests",
            metadata={"sections": request.sections},
        )
        agent_input.job_id = job.job_id
        await job_manager.update_job_status(
            job.job_id, JobStatus.PROCESSING, "Autotest generation started"
        )

        file_storage.create_job_directory(job.job_id)
        background_tasks.add_task(
            process_api_autotest_results,
            job.job_id,
            agent,
            agent_input,
            job_manager,
            file_storage,
        )

        return await job_manager.get_job_status(job.job_id) or job

    except HTTPException:
        raise
    except TestOpsException as exc:
        logger.error(f"TestOps error in API autotest generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in API autotest generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_autotest_generation_status(
    job_id: UUID,
    job_manager: JobManager = Depends(get_job_manager),
) -> JobStatusResponse:
    """Get autotest generation status."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    if job.status == JobStatus.COMPLETED:
        job.download_url = f"/api/v1/autotests/{job_id}/download"
    return job


@router.get("/{job_id}/download")
async def download_autotests(
    job_id: UUID,
    file_storage: FileStorage = Depends(get_file_storage),
) -> FileResponse:
    """Download generated autotests as zip."""
    archive_path = file_storage.create_zip_archive(job_id, prefix="autotests_")
    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No autotests found for job {job_id}",
        )

    return FileResponse(
        path=archive_path,
        filename=f"autotests_{job_id}.zip",
        media_type="application/zip",
    )


async def process_ui_autotest_results(
    job_id: UUID,
    agent: ManualToUITestsAgent,
    agent_input: ManualToUITestsInput,
    job_manager: JobManager,
    file_storage: FileStorage,
):
    """Run UI autotest generation and persist artifacts."""
    try:
        agent_input.job_id = job_id
        result = await agent.execute(agent_input)

        if result.success and result.generated_tests:
            for test in result.generated_tests:
                file_storage.save_test_file(
                    job_id=job_id,
                    filename=test.filename,
                    content=test.test_file,
                )
            await job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                f"UI autotests generated: {len(result.generated_tests)} files",
            )
        else:
            await job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                f"UI autotest generation failed: {result.error}",
            )
    except Exception as exc:
        logger.error(f"Error processing UI autotests for job {job_id}: {exc}")
        await job_manager.update_job_status(
            job_id, JobStatus.FAILED, f"Error processing results: {exc}"
        )


async def process_api_autotest_results(
    job_id: UUID,
    agent: OpenAPIToAPITestsAgent,
    agent_input: OpenAPIToAPITestsInput,
    job_manager: JobManager,
    file_storage: FileStorage,
):
    """Run API autotest generation and persist artifacts."""
    try:
        agent_input.job_id = job_id
        result = await agent.execute(agent_input)

        if result.success and result.generated_tests:
            for test in result.generated_tests:
                file_storage.save_test_file(
                    job_id=job_id,
                    filename=test.filename,
                    content=test.test_file,
                )
            await job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                f"API autotests generated: {len(result.generated_tests)} files",
            )
        else:
            await job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                f"API autotest generation failed: {result.error}",
            )
    except Exception as exc:
        logger.error(f"Error processing API autotests for job {job_id}: {exc}")
        await job_manager.update_job_status(
            job_id, JobStatus.FAILED, f"Error processing results: {exc}"
        )
