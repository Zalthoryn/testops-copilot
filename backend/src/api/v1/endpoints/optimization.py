"""
API endpoints for test suite optimization.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse

from src.models.dto import (
    JobResponse,
    JobStatusResponse,
    OptimizationRequest,
    OptimizationResult,
)
from src.models.enums import JobStatus
from src.services.job_manager import JobManager, get_job_manager
from src.services.llm_client import LLMClient, get_llm_client
from src.agents.optimization_agent import OptimizationAgent, OptimizationInput
from src.storage.file_storage import FileStorage, get_file_storage
from src.utils.logger import get_logger
from src.utils.exceptions import TestOpsException

router = APIRouter(prefix="/optimization", tags=["optimization"])
logger = get_logger(__name__)


@router.post("/analyze", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_test_coverage(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    llm_client: LLMClient = Depends(get_llm_client),
    job_manager: JobManager = Depends(get_job_manager),
    file_storage: FileStorage = Depends(get_file_storage),
) -> JobResponse:
    """Run optimization analysis for provided test cases."""
    try:
        # TODO: replace stubbed testcases with repository parsing when available
        from src.models.dto import TestCaseDTO, TestType, TestPriority

        testcases = [
            TestCaseDTO(
                id=UUID(int=i + 1),
                title=f"Test Case {i + 1}",
                feature="Sample Feature",
                story="Sample Story",
                priority=TestPriority.NORMAL,
                steps=["Step 1", "Step 2"],
                expected_result="Expected result",
                python_code="",
                test_type=TestType.MANUAL_UI,
                owner="qa_team",
            )
            for i in range(5)
        ]

        agent = OptimizationAgent(llm_client)
        agent_input = OptimizationInput(
            job_id=UUID(int=0),
            testcases=testcases,
            requirements_text=request.requirements,
            checks=request.checks,
            similarity_threshold=0.8,
        )

        job = await job_manager.create_job(job_type="optimization")
        agent_input.job_id = job.job_id
        await job_manager.update_job_status(
            job.job_id, JobStatus.PROCESSING, "Optimization started"
        )

        file_storage.create_job_directory(job.job_id)
        background_tasks.add_task(
            process_optimization_results,
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
        logger.error(f"TestOps error in optimization: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in optimization: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_optimization_status(
    job_id: UUID, job_manager: JobManager = Depends(get_job_manager)
) -> JobStatusResponse:
    """Get optimization job status."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    return job


@router.get("/{job_id}/download")
async def download_optimized_tests(
    job_id: UUID, file_storage: FileStorage = Depends(get_file_storage)
) -> FileResponse:
    """Download optimized artifacts."""
    archive_path = file_storage.create_zip_archive(job_id, prefix="optimized_")
    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No optimized tests found for job {job_id}",
        )

    return FileResponse(
        path=archive_path,
        filename=f"optimized_tests_{job_id}.zip",
        media_type="application/zip",
    )


async def process_optimization_results(
    job_id: UUID,
    agent: OptimizationAgent,
    agent_input: OptimizationInput,
    job_manager: JobManager,
    file_storage: FileStorage,
):
    """Run optimization agent and persist results."""
    try:
        agent_input.job_id = job_id
        result = await agent.execute(agent_input)

        if result.success:
            import json

            analysis_file = file_storage.get_job_directory(job_id) / "optimization.json"
            with open(analysis_file, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "analysis": result.analysis,
                        "recommendations": result.recommendations,
                    },
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )

            await job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                "Optimization analysis completed",
            )
        else:
            await job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                f"Optimization failed: {result.error}",
            )
    except Exception as exc:
        logger.error(f"Error processing optimization results for job {job_id}: {exc}")
        await job_manager.update_job_status(
            job_id, JobStatus.FAILED, f"Error processing results: {exc}"
        )
