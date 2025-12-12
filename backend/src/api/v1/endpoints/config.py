# backend/src/api/v1/endpoints/config.py
"""
API endpoints для управления конфигурацией системы
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import os

from ....models.dto import ConfigResponse, ComputeValidationRequest, ComputeValidationResponse
from ....services.llm_client import LLMClient, get_llm_client
from ....services.compute_api_client import EvolutionComputeClient, get_compute_client
from ....services.gitlab_client import GitLabClient, get_gitlab_client
from ....utils.logger import get_logger
from ....utils.exceptions import TestOpsException

logger = get_logger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """
    Получение текущих настроек системы
    
    Returns:
        Конфигурация системы
    """
    try:
        logger.info("Getting system configuration")
        
        # Проверяем доступность LLM
        llm_client = get_llm_client()
        llm_available = await llm_client.validate_connection()
        
        # Проверяем доступность Compute API
        compute_client = get_compute_client()
        compute_status = await compute_client.validate_connection()
        
        # Проверяем доступность GitLab
        gitlab_client = get_gitlab_client()
        gitlab_status = await gitlab_client.validate_connection()
        
        return ConfigResponse(
            llm_model=os.getenv("CLOUDRU_LLM_MODEL", "evolution-foundation"),
            compute_endpoint=os.getenv("EVOLUTION_COMPUTE_URL", "https://compute.api.cloud.ru"),
            gitlab_configured=gitlab_status.get("authenticated", False),
            llm_available=llm_available,
            compute_available=compute_status.get("available", False),
            environment=os.getenv("ENVIRONMENT", "development")
        )
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/compute/validate", response_model=ComputeValidationResponse)
async def validate_compute_connection(
    request: ComputeValidationRequest
) -> ComputeValidationResponse:
    """
    Валидация доступа к Evolution Compute API
    
    - **token**: Токен аутентификации
    - **key_id**: Key ID для аутентификации
    - **secret**: Secret для аутентификации
    """
    try:
        logger.info("Validating Compute API connection")
        
        # Создаем клиент с переданными учетными данными
        compute_client = EvolutionComputeClient(
            api_token=request.token,
            key_id=request.key_id,
            secret=request.secret
        )
        
        # Проверяем соединение
        validation_result = await compute_client.validate_connection()
        
        return ComputeValidationResponse(
            valid=validation_result["available"],
            endpoint=validation_result["endpoint"],
            available_resources=[
                "vms" if validation_result.get("virtual_machines_count", 0) > 0 else "",
                "disks" if validation_result.get("disks_count", 0) > 0 else "",
                "flavors" if validation_result.get("flavors_count", 0) > 0 else ""
            ],
            error=validation_result.get("error")
        )
        
    except TestOpsException as e:
        logger.error(f"TestOps error in Compute validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in Compute validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/gitlab/validate")
async def validate_gitlab_connection(
    token: str,
    project_id: str,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Валидация доступа к GitLab
    
    - **token**: GitLab Personal Access Token
    - **project_id**: ID проекта GitLab
    - **base_url**: URL GitLab (опционально)
    """
    try:
        logger.info("Validating GitLab connection")
        
        gitlab_client = GitLabClient(
            access_token=token,
            project_id=project_id,
            base_url=base_url
        )
        
        validation_result = await gitlab_client.validate_connection()
        
        return {
            "valid": validation_result["available"],
            "authenticated": validation_result.get("authenticated", False),
            "project": validation_result.get("project"),
            "error": validation_result.get("error")
        }
        
    except TestOpsException as e:
        logger.error(f"TestOps error in GitLab validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in GitLab validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/llm/validate")
async def validate_llm_connection(
    api_key: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Валидация доступа к LLM API
    
    - **api_key**: API ключ для LLM
    - **model**: Модель LLM (опционально)
    - **base_url**: URL LLM API (опционально)
    """
    try:
        logger.info("Validating LLM connection")
        
        llm_client = LLMClient(
            api_key=api_key,
            model=model,
            base_url=base_url
        )
        
        is_valid = await llm_client.validate_connection()
        
        return {
            "valid": is_valid,
            "model": model or "evolution-foundation",
            "base_url": base_url or "https://llm.api.cloud.ru/v1"
        }
        
    except TestOpsException as e:
        logger.error(f"TestOps error in LLM validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in LLM validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health/detailed")
async def get_detailed_health() -> Dict[str, Any]:
    """
    Получение детальной информации о состоянии системы
    
    Returns:
        Детальная информация о здоровье системы
    """
    try:
        logger.info("Getting detailed health information")
        
        health_info = {
            "status": "healthy",
            "components": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Проверяем LLM
        try:
            llm_client = get_llm_client()
            llm_health = await llm_client.health_check()
            health_info["components"]["llm"] = llm_health
            if not llm_health["connected"]:
                health_info["status"] = "degraded"
        except Exception as e:
            health_info["components"]["llm"] = {
                "status": "unavailable",
                "error": str(e)
            }
            health_info["status"] = "degraded"
        
        # Проверяем Compute API
        try:
            compute_client = get_compute_client()
            compute_health = await compute_client.health_check()
            health_info["components"]["compute_api"] = compute_health
            if not compute_health["available"]:
                health_info["status"] = "degraded"
        except Exception as e:
            health_info["components"]["compute_api"] = {
                "status": "unavailable",
                "error": str(e)
            }
            health_info["status"] = "degraded"
        
        # Проверяем GitLab
        try:
            gitlab_client = get_gitlab_client()
            gitlab_health = await gitlab_client.health_check()
            health_info["components"]["gitlab"] = gitlab_health
        except Exception as e:
            health_info["components"]["gitlab"] = {
                "status": "unavailable",
                "error": str(e)
            }
        
        # Проверяем Redis (если используется)
        try:
            # TODO: Реализовать проверку Redis
            health_info["components"]["redis"] = {
                "status": "unknown",
                "message": "Redis check not implemented"
            }
        except Exception as e:
            health_info["components"]["redis"] = {
                "status": "unavailable",
                "error": str(e)
            }
        
        return health_info
        
    except Exception as e:
        logger.error(f"Error getting detailed health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )