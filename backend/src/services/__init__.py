"""
Сервисы для TestOps Copilot
"""
from .compute_api_client import EvolutionComputeClient, get_compute_client
from .llm_client import LLMClient, get_llm_client
from .job_manager import JobManager, get_job_manager

__all__ = [
    'EvolutionComputeClient',
    'get_compute_client',
    'LLMClient',
    'get_llm_client',
    'JobManager',
    'get_job_manager',
]