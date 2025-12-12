"""
Agent for generating automated API tests from an OpenAPI specification.
"""
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.models.enums import TestType
from src.services.llm_client import LLMClient
from src.services.openapi_parser import OpenAPIParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class APITestFile(BaseModel):
    filename: str
    test_file: str
    test_count: int
    framework: str
    http_client: str
    sections: List[str]


class OpenAPIToAPITestsInput(AgentInput):
    """Input for API autotest generation."""

    openapi_url: Optional[str] = Field(default=None)
    openapi_content: Optional[str] = Field(default=None)
    sections: List[str] = Field(
        default_factory=lambda: ["vms", "disks", "flavors"]
    )
    base_url: str = Field(default="https://compute.api.cloud.ru")
    auth_token: Optional[str] = Field(default=None)
    test_framework: str = Field(default="pytest")
    http_client: str = Field(default="httpx")
    target_count: int = Field(default=10, ge=1, le=50)


class OpenAPIToAPITestsOutput(AgentOutput):
    """Result with generated API autotests."""

    generated_tests: List[APITestFile] = Field(default_factory=list)
    total_tests: int = 0
    framework: str = "pytest"
    http_client: str = "httpx"
    sections_covered: List[str] = Field(default_factory=list)


class OpenAPIToAPITestsAgent(
    BaseAgent[OpenAPIToAPITestsInput, OpenAPIToAPITestsOutput]
):
    """Generate pytest-based API autotests from OpenAPI."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)
        self.parser = OpenAPIParser()

    def get_system_prompt(self) -> str:
        return (
            "You are a backend QA automation engineer. "
            "Generate pytest API tests using the provided endpoints. "
            "Use the specified HTTP client and return JSON with 'tests': "
            "[{'filename': ..., 'python_code': ..., 'test_count': <int>}]."
        )

    async def execute(
        self, input_data: OpenAPIToAPITestsInput
    ) -> OpenAPIToAPITestsOutput:
        self.log_progress("Preparing OpenAPI spec for API autotests")
        try:
            spec = await self._load_spec(input_data)
            filtered = self._filter_by_sections(spec, input_data.sections)
            endpoints = self._summarize_endpoints(filtered)

            if not endpoints:
                raise ValueError("No endpoints found for the requested sections")

            prompt = self._build_prompt(input_data, endpoints)
            generated_files: List[APITestFile] = []

            try:
                response = await self.generate_structured_response(prompt, 0.35)
                generated_files = self._parse_response(response, input_data)
            except Exception as llm_error:
                self.log_error("LLM failed to return structured tests", llm_error)

            if not generated_files:
                generated_files = self._fallback_tests(endpoints, input_data)

            total = sum(test.test_count for test in generated_files)
            self.log_progress(f"Generated {total} API autotests")

            return OpenAPIToAPITestsOutput(
                success=True,
                generated_tests=generated_files,
                total_tests=total,
                framework=input_data.test_framework,
                http_client=input_data.http_client,
                sections_covered=input_data.sections,
            )
        except Exception as exc:
            self.log_error("Failed to generate API autotests", exc)
            return OpenAPIToAPITestsOutput(
                success=False, error=str(exc), generated_tests=[]
            )

    async def _load_spec(self, input_data: OpenAPIToAPITestsInput) -> Dict[str, object]:
        if input_data.openapi_content:
            return self.parser.parse_from_content(input_data.openapi_content)
        if input_data.openapi_url:
            return await self.parser.parse_from_url(input_data.openapi_url)
        raise ValueError("Either openapi_url or openapi_content is required")

    def _filter_by_sections(
        self, spec: Dict[str, object], sections: List[str]
    ) -> Dict[str, object]:
        return self.parser.filter_by_tags(spec, sections) if sections else spec

    def _summarize_endpoints(self, spec: Dict[str, object]) -> List[Dict[str, str]]:
        endpoints: List[Dict[str, str]] = []
        for path, methods in spec.get("paths", {}).items():
            for method, definition in methods.items():
                endpoints.append(
                    {
                        "signature": f"{method.upper()} {path}",
                        "summary": definition.get("summary", ""),
                    }
                )
        return endpoints[:100]

    def _build_prompt(
        self, input_data: OpenAPIToAPITestsInput, endpoints: List[Dict[str, str]]
    ) -> str:
        endpoint_lines = "\n".join(
            f"- {ep['signature']}: {ep['summary']}" for ep in endpoints
        )
        auth_hint = (
            "Use bearer token from AUTH_TOKEN env var if required."
            if input_data.auth_token
            else "Assume no auth if token not provided."
        )
        return (
            f"Framework: {input_data.test_framework}\n"
            f"HTTP client: {input_data.http_client}\n"
            f"Base URL: {input_data.base_url}\n"
            f"{auth_hint}\n"
            "Endpoints:\n"
            f"{endpoint_lines}\n\n"
            "Return JSON with 'tests': "
            "[{'filename': 'test_api_x.py', 'python_code': '...pytest code...', 'test_count': 1}]."
        )

    def _parse_response(
        self, response: Dict[str, object], input_data: OpenAPIToAPITestsInput
    ) -> List[APITestFile]:
        tests = response.get("tests") if isinstance(response, dict) else None
        if not tests:
            return []

        files: List[APITestFile] = []
        for idx, test in enumerate(tests):
            try:
                filename = test.get("filename") if isinstance(test, dict) else None
                code = test.get("python_code") if isinstance(test, dict) else None
                if not filename:
                    filename = f"test_api_{idx + 1}.py"
                if not code:
                    continue

                files.append(
                    APITestFile(
                        filename=self._sanitize_filename(filename),
                        test_file=code,
                        test_count=int(test.get("test_count", 1)),
                        framework=input_data.test_framework,
                        http_client=input_data.http_client,
                        sections=input_data.sections,
                    )
                )
            except Exception as parse_error:
                self.log_error("Failed to parse API test from LLM", parse_error)
                continue
        return files

    def _fallback_tests(
        self, endpoints: List[Dict[str, str]], input_data: OpenAPIToAPITestsInput
    ) -> List[APITestFile]:
        files: List[APITestFile] = []
        for endpoint in endpoints[: input_data.target_count]:
            filename = self._sanitize_filename(
                f"test_{endpoint['signature'].replace(' ', '_')}.py"
            )
            code = self._build_stub(endpoint, input_data)
            files.append(
                APITestFile(
                    filename=filename,
                    test_file=code,
                    test_count=1,
                    framework=input_data.test_framework,
                    http_client=input_data.http_client,
                    sections=input_data.sections,
                )
            )
        return files

    def _build_stub(
        self, endpoint: Dict[str, str], input_data: OpenAPIToAPITestsInput
    ) -> str:
        method, path = endpoint["signature"].split(" ", 1)
        function_name = self._to_test_name(f"{method}_{path.replace('/', '_')}")
        return (
            "import os\n"
            "import pytest\n"
            "import allure\n"
            f"import {input_data.http_client} as http_client\n\n"
            f"BASE_URL = '{input_data.base_url}'\n"
            "AUTH_TOKEN = os.getenv('AUTH_TOKEN', '')\n\n"
            f"@allure.feature('Compute API')\n"
            f"@allure.story('{endpoint['signature']}')\n"
            f"def {function_name}():\n"
            f"    url = f\"{input_data.base_url}{path}\"\n"
            "    headers = {}\n"
            "    if AUTH_TOKEN:\n"
            "        headers['Authorization'] = f'Bearer {AUTH_TOKEN}'\n"
            f"    response = http_client.request('{method}', url, headers=headers)\n"
            "    assert response.status_code < 400\n"
        )

    def _sanitize_filename(self, value: str) -> str:
        import re

        clean = re.sub(r"[^\w\-\.]", "_", value.strip().lower())
        return clean or "test_api.py"
