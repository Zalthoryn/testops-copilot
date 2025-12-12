"""
API endpoints for standards validation (AAA, Allure, naming).
"""
import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from src.models.dto import JobResponse, JobStatusResponse, StandardsCheckRequest, StandardsReport
from src.models.enums import JobStatus
from src.services.job_manager import JobManager, get_job_manager
from src.services.llm_client import LLMClient, get_llm_client
from src.agents.standards_agent import StandardsAgent, StandardsCheckInput
from src.storage.file_storage import FileStorage, get_file_storage
from src.utils.logger import get_logger
from src.utils.exceptions import TestOpsException

router = APIRouter(prefix="/standards", tags=["standards"])
logger = get_logger(__name__)


@router.post("/check", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def check_standards(
    files: List[UploadFile] = File(...),
    checks: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    llm_client: LLMClient = Depends(get_llm_client),
    job_manager: JobManager = Depends(get_job_manager),
    file_storage: FileStorage = Depends(get_file_storage),
) -> JobResponse:
    """Run static checks on uploaded test files."""
    try:
        file_contents = []
        for uploaded_file in files:
            content = await uploaded_file.read()
            file_contents.append(
                {"filename": uploaded_file.filename, "content": content.decode("utf-8")}
            )

        agent = StandardsAgent(llm_client)
        agent_input = StandardsCheckInput(
            job_id=UUID(int=0),
            files=file_contents,
            checks=checks or ["aaa", "allure", "naming"],
        )

        job = await job_manager.create_job(
            job_type="standards_check", metadata={"files": len(file_contents)}
        )
        agent_input.job_id = job.job_id
        await job_manager.update_job_status(
            job.job_id, JobStatus.PROCESSING, "Standards check started"
        )

        file_storage.create_job_directory(job.job_id)
        for file_info in file_contents:
            file_storage.save_standards_file(
                job_id=job.job_id,
                filename=file_info["filename"],
                content=file_info["content"],
            )

        background_tasks.add_task(
            process_standards_check_results,
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
        logger.error(f"TestOps error in standards check: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Unexpected error in standards check: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_standards_status(
    job_id: UUID, job_manager: JobManager = Depends(get_job_manager)
) -> JobStatusResponse:
    """Get standards check job status."""
    job = await job_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )
    if job.status == JobStatus.COMPLETED:
        job.download_url = f"/api/v1/standards/{job_id}/download"
    return job


@router.get("/{job_id}/download")
async def download_standards_report(
    job_id: UUID, file_storage: FileStorage = Depends(get_file_storage)
) -> FileResponse:
    """Download standards report archive."""
    archive_path = file_storage.create_zip_archive(job_id, prefix="standards_")
    if not archive_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No standards report for job {job_id}",
        )

    return FileResponse(
        path=archive_path,
        filename=f"standards_{job_id}.zip",
        media_type="application/zip",
    )


async def process_standards_check_results(
    job_id: UUID,
    agent: StandardsAgent,
    agent_input: StandardsCheckInput,
    job_manager: JobManager,
    file_storage: FileStorage,
):
    """Run standards agent and persist reports."""
    try:
        agent_input.job_id = job_id
        result = await agent.execute(agent_input)

        if result.success and result.report:
            report = result.report
            report_path = file_storage.get_job_directory(job_id) / "standards_report.json"
            with open(report_path, "w", encoding="utf-8") as handle:
                json.dump(report.model_dump(), handle, indent=2, ensure_ascii=False)

            html_report = _create_html_report(report)
            html_file = file_storage.get_job_directory(job_id) / "standards_report.html"
            with open(html_file, "w", encoding="utf-8") as handle:
                handle.write(html_report)

            await job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                f"Standards check completed: {report.total_violations} violations",
            )
        else:
            await job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                f"Standards check failed: {result.error}",
            )
    except Exception as exc:
        logger.error(f"Error processing standards job {job_id}: {exc}")
        await job_manager.update_job_status(
            job_id, JobStatus.FAILED, f"Error processing results: {exc}"
        )


def _create_html_report(report: StandardsReport) -> str:
    """Create a simple HTML report for standards check."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Standards Check Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .violation {{ border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .error {{ border-left: 5px solid #dc3545; }}
        .warning {{ border-left: 5px solid #ffc107; }}
        .info {{ border-left: 5px solid #17a2b8; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Standards Check Report</h1>
        <p>Job ID: {report.job_id}</p>
        <p>Generated at: {report.generated_at}</p>
        <p>Total files: {report.total_files}</p>
        <p>Total violations: {report.total_violations}</p>
    </div>
    <div class="violations">
        {"".join([
            f'<div class="violation {v.severity}">'
            f'<p><strong>{v.severity.upper()}</strong> in {v.file} at line {v.line}</p>'
            f'<p>Rule: {v.rule}</p>'
            f'<p>Message: {v.message}</p>'
            f'<p>Suggested fix: {v.suggested_fix}</p>'
            f'</div>'
            for v in report.violations
        ])}
    </div>
</body>
</html>"""
