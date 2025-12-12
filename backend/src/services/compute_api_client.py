"""
Async client for Cloud.ru Compute API (based on cloud_docs.yaml).
"""
from typing import Any, Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils.exceptions import AuthenticationException, ComputeAPIException
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EvolutionComputeClient:
    """Minimal Compute API client supporting the documented endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.base_url = base_url or settings.COMPUTE_API_URL
        self.api_token = api_token or settings.COMPUTE_API_TOKEN
        default_headers = (
            {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        )
        self.http_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=settings.API_TIMEOUT,
            headers=default_headers,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _request(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        try:
            response = await self.http_client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Compute API error %s for %s %s: %s",
                exc.response.status_code,
                method,
                url,
                exc.response.text,
            )
            if exc.response.status_code == 401:
                raise AuthenticationException("Invalid or missing Compute API token")
            raise ComputeAPIException(f"API error: {exc.response.status_code}")
        except httpx.RequestError as exc:
            logger.error("Network error calling Compute API: %s", exc)
            raise ComputeAPIException(f"Network error: {exc}")

    async def get_flavors(self, params: Optional[Dict[str, Any]] = None, **kwargs) -> List[Dict]:
        query = params or kwargs or {}
        response = await self._request("GET", "/api/v1/flavors", params=query)
        return response.json() if response.content else []

    async def get_disks(self, params: Optional[Dict[str, Any]] = None, **kwargs) -> List[Dict]:
        query = params or kwargs or {}
        response = await self._request("GET", "/api/v1/disks", params=query)
        return response.json() if response.content else []

    async def get_virtual_machines(
        self, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[Dict]:
        query = params or kwargs or {}
        response = await self._request("GET", "/api/v1/vms", params=query)
        return response.json() if response.content else []

    async def validate_connection(self) -> Dict[str, Any]:
        """Check basic availability of the API."""
        try:
            flavors = await self.get_flavors({"limit": 1})
            vms = await self.get_virtual_machines({"limit": 1})
            disks = await self.get_disks({"limit": 1})
            return {
                "available": True,
                "endpoint": self.base_url,
                "flavors_count": len(flavors),
                "virtual_machines_count": len(vms),
                "disks_count": len(disks),
                "authenticated": True,
            }
        except AuthenticationException as exc:
            return {
                "available": False,
                "endpoint": self.base_url,
                "error": str(exc),
                "authenticated": False,
            }
        except Exception as exc:
            return {
                "available": False,
                "endpoint": self.base_url,
                "error": str(exc),
                "authenticated": False,
            }

    async def health_check(self) -> Dict[str, Any]:
        status = await self.validate_connection()
        status_code = "healthy" if status.get("available") else "degraded"
        return {
            "status": status_code,
            "base_url": self.base_url,
            "authenticated": status.get("authenticated", False),
            "available": status.get("available", False),
            "error": status.get("error"),
            "statistics": {
                "flavors_seen": status.get("flavors_count", 0),
                "vms_seen": status.get("virtual_machines_count", 0),
                "disks_seen": status.get("disks_count", 0),
            },
        }

    async def close(self):
        await self.http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


async def get_compute_client() -> EvolutionComputeClient:
    """Factory for dependency injection."""
    return EvolutionComputeClient()


def get_sync_compute_client() -> EvolutionComputeClient:
    import asyncio

    return asyncio.run(get_compute_client())
