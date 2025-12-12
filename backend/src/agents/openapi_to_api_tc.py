"""
Agent for generating manual API test cases from an OpenAPI specification.
"""
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.models.dto import TestCaseDTO
from src.models.enums import TestPriority, TestType
from src.services.llm_client import LLMClient
from src.services.openapi_parser import OpenAPIParser
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAPIToAPITCInput(AgentInput):
    """Input for manual API test case generation."""

    openapi_url: Optional[str] = Field(
        default=None, description="URL to the OpenAPI document"
    )
    openapi_content: Optional[str] = Field(
        default=None, description="Raw OpenAPI content (YAML or JSON)"
    )
    sections: List[str] = Field(
        default_factory=lambda: ["vms", "disks", "flavors"],
        description="Tags/sections to keep from the spec",
    )
    auth_type: Optional[str] = Field(default="bearer")
    target_count: int = Field(default=30, ge=1, le=100)
    priority: TestPriority = Field(default=TestPriority.NORMAL)
    owner: str = Field(default="api_qa_team")
    base_url: Optional[str] = Field(default="https://compute.api.cloud.ru")


class OpenAPIToAPITCOutput(AgentOutput):
    """Result with generated manual API cases."""

    testcases: List[TestCaseDTO] = Field(default_factory=list)
    total_generated: int = 0
    endpoints_covered: List[str] = Field(default_factory=list)


class OpenAPIToAPITCAgent(
    BaseAgent[OpenAPIToAPITCInput, OpenAPIToAPITCOutput]
):
    """Generate manual API test cases based on an OpenAPI description."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)
        self.parser = OpenAPIParser()
        self.section_tags = {
            "vms": ["VMs", "vms"],
            "disks": ["Disks", "disks"],
            "flavors": ["Flavors", "flavors"],
        }

    def get_system_prompt(self) -> str:
        return (
            "You are a senior API QA engineer. "
            "Generate concise manual API test cases in Allure style. "
            "Prefer AAA structure and provide JSON with key 'testcases' only."
        )

    async def execute(
        self, input_data: OpenAPIToAPITCInput
    ) -> OpenAPIToAPITCOutput:
        self.log_progress("Loading OpenAPI specification")
        try:
            spec = await self._load_spec(input_data)
            filtered = self._filter_by_sections(spec, input_data.sections)
            endpoints = self._summarize_endpoints(filtered)

            if not endpoints:
                raise ValueError("No endpoints found for the selected sections")

            prompt = self._build_prompt(input_data, endpoints)
            testcases: List[TestCaseDTO] = []

            try:
                response = await self.generate_structured_response(prompt, 0.25)
                testcases = self._parse_response(response, input_data)
            except Exception as llm_error:
                self.log_error("LLM JSON generation failed, using fallback", llm_error)

            if not testcases:
                testcases = self._fallback_cases(endpoints, input_data)

            self.log_progress(f"Prepared {len(testcases)} API test cases")
            return OpenAPIToAPITCOutput(
                success=True,
                testcases=testcases,
                total_generated=len(testcases),
                endpoints_covered=[e["signature"] for e in endpoints],
            )
        except Exception as exc:
            self.log_error("Failed to build API test cases", exc)
            return OpenAPIToAPITCOutput(
                success=False, error=str(exc), testcases=[], total_generated=0
            )

    async def _load_spec(self, input_data: OpenAPIToAPITCInput) -> Dict[str, object]:
        if input_data.openapi_content:
            return self.parser.parse_from_content(input_data.openapi_content)
        if input_data.openapi_url:
            return await self.parser.parse_from_url(input_data.openapi_url)
        raise ValueError("Either openapi_url or openapi_content is required")

    def _filter_by_sections(
        self, spec: Dict[str, object], sections: List[str]
    ) -> Dict[str, object]:
        tags: List[str] = []
        for section in sections:
            tags.extend(self.section_tags.get(section, [section]))
        return self.parser.filter_by_tags(spec, tags) if tags else spec

    def _summarize_endpoints(self, spec: Dict[str, object]) -> List[Dict[str, str]]:
        endpoints: List[Dict[str, str]] = []
        for path, methods in spec.get("paths", {}).items():
            for method, definition in methods.items():
                endpoints.append(
                    {
                        "signature": f"{method.upper()} {path}",
                        "summary": definition.get("summary", ""),
                        "tags": definition.get("tags", []),
                    }
                )
        return endpoints[:100]

    def _build_prompt(
        self, input_data: OpenAPIToAPITCInput, endpoints: List[Dict[str, str]]
    ) -> str:
        endpoint_lines = "\n".join(
            f"- {ep['signature']}: {ep['summary']}" for ep in endpoints
        )
        return (
            f"Base URL: {input_data.base_url}\n"
            f"Auth type: {input_data.auth_type}\n"
            f"Priority: {input_data.priority.value}\n"
            f"Target count: {input_data.target_count}\n"
            "Endpoints:\n"
            f"{endpoint_lines}\n\n"
            "Return JSON with 'testcases' list. "
            "Each item must have title, feature, story, steps, expected_result, and optionally python_code."
        )

    def _parse_response(
        self, response: Dict[str, object], input_data: OpenAPIToAPITCInput
    ) -> List[TestCaseDTO]:
        raw_cases = response.get("testcases") if isinstance(response, dict) else None
        if not raw_cases:
            return []

        results: List[TestCaseDTO] = []
        for idx, tc in enumerate(raw_cases):
            try:
                title = tc.get("title") if isinstance(tc, dict) else None
                feature = tc.get("feature") if isinstance(tc, dict) else "API"
                story = tc.get("story") if isinstance(tc, dict) else "API path coverage"
                steps = tc.get("steps") if isinstance(tc, dict) else []
                expected = (
                    tc.get("expected_result")
                    if isinstance(tc, dict)
                    else "API returns expected response"
                )
                python_code = (
                    tc.get("python_code") if isinstance(tc, dict) else None
                ) or self.generate_allure_code(
                    feature=feature,
                    story=story,
                    title=title or f"API Test {idx + 1}",
                    steps=steps,
                    test_type=TestType.MANUAL_API,
                    is_manual=True,
                )

                results.append(
                    self.create_testcase(
                        title=title or f"API Test {idx + 1}",
                        feature=feature,
                        story=story,
                        steps=steps,
                        expected_result=expected,
                        python_code=python_code,
                        test_type=TestType.MANUAL_API,
                        priority=tc.get("priority", input_data.priority),
                        owner=input_data.owner,
                    )
                )
            except Exception as parse_error:
                self.log_error("Failed to parse testcase from LLM", parse_error)
                continue
        return results

    def _fallback_cases(
        self, endpoints: List[Dict[str, str]], input_data: OpenAPIToAPITCInput
    ) -> List[TestCaseDTO]:
        fallback: List[TestCaseDTO] = []
        limit = max(1, min(input_data.target_count, len(endpoints)))
        for endpoint in endpoints[:limit]:
            steps = [
                f"Prepare request for {endpoint['signature']}",
                "Send request with required headers/auth",
                "Validate status code and response schema",
            ]
            python_code = self.generate_allure_code(
                feature="Compute API",
                story=endpoint["signature"],
                title=f"{endpoint['signature']} behaves as expected",
                steps=steps,
                test_type=TestType.MANUAL_API,
                is_manual=True,
            )
            fallback.append(
                self.create_testcase(
                    title=f"{endpoint['signature']} validation",
                    feature="Compute API",
                    story=endpoint["signature"],
                    steps=steps,
                    expected_result="Response matches specification",
                    python_code=python_code,
                    test_type=TestType.MANUAL_API,
                    priority=input_data.priority,
                    owner=input_data.owner,
                )
            )
        return fallback
