"""
Agent that turns manual UI test cases into Playwright-based automated tests.
"""
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.models.dto import TestCaseDTO
from src.models.enums import TestPriority
from src.services.llm_client import LLMClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class GeneratedTestFile(BaseModel):
    """Container for a generated autotest file."""

    filename: str
    test_file: str
    test_count: int
    framework: str
    browsers: List[str]


class ManualToUITestsInput(AgentInput):
    """Input payload for UI autotest generation."""

    testcases: List[TestCaseDTO]
    framework: str = Field(default="playwright")
    browsers: List[str] = Field(default_factory=lambda: ["chromium"])
    base_url: str = Field(default="https://cloud.ru/calculator")
    headless: bool = Field(default=True)
    viewport: Dict[str, int] = Field(
        default_factory=lambda: {"width": 1920, "height": 1080}
    )
    timeout: int = Field(default=30000)
    priority_filter: Optional[List[str]] = Field(default=None)


class ManualToUITestsOutput(AgentOutput):
    """Agent output with generated UI autotests."""

    generated_tests: List[GeneratedTestFile] = Field(default_factory=list)
    total_tests: int = 0
    framework: str = "playwright"
    browsers: List[str] = Field(default_factory=list)


class ManualToUITestsAgent(
    BaseAgent[ManualToUITestsInput, ManualToUITestsOutput]
):
    """Generate Playwright autotests from manual UI test cases."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)

    def get_system_prompt(self) -> str:
        return (
            "You are a senior QA automation engineer. "
            "Convert the provided manual UI test cases into Playwright + pytest tests. "
            "Use Allure annotations (feature, story, title) and keep steps as comments. "
            "Return JSON with a list 'tests', each item containing filename, "
            "python_code, and test_count."
        )

    async def execute(
        self, input_data: ManualToUITestsInput
    ) -> ManualToUITestsOutput:
        self.log_progress("Starting UI autotest generation")
        try:
            filtered = self._filter_by_priority(
                input_data.testcases, input_data.priority_filter
            )
            if not filtered:
                return ManualToUITestsOutput(
                    success=False,
                    error="No testcases to convert after applying priority filter",
                )

            prompt = self._build_prompt(input_data, filtered)
            generated_files: List[GeneratedTestFile] = []

            try:
                response = await self.generate_structured_response(prompt, 0.35)
                generated_files = self._parse_response(response, input_data)
            except Exception as llm_error:
                self.log_error("LLM generation failed, falling back", llm_error)

            if not generated_files:
                generated_files = [
                    self._fallback_file(tc, input_data) for tc in filtered
                ]

            total_tests = sum(file.test_count for file in generated_files)
            self.log_progress(f"Generated {total_tests} UI autotests")

            return ManualToUITestsOutput(
                success=True,
                generated_tests=generated_files,
                total_tests=total_tests,
                framework=input_data.framework,
                browsers=input_data.browsers,
            )

        except Exception as exc:
            self.log_error("Failed to generate UI autotests", exc)
            return ManualToUITestsOutput(
                success=False, error=str(exc), generated_tests=[]
            )

    def _filter_by_priority(
        self, testcases: List[TestCaseDTO], priority_filter: Optional[List[str]]
    ) -> List[TestCaseDTO]:
        if not priority_filter:
            return testcases

        normalized = {p.upper() for p in priority_filter}
        return [tc for tc in testcases if tc.priority.value in normalized]

    def _build_prompt(
        self, input_data: ManualToUITestsInput, testcases: List[TestCaseDTO]
    ) -> str:
        cases_summary = []
        for idx, tc in enumerate(testcases, start=1):
            cases_summary.append(
                f"{idx}. {tc.title}\n"
                f"Feature: {tc.feature}; Story: {tc.story}; Priority: {tc.priority}\n"
                f"Steps: {tc.steps}\n"
                f"Expected: {tc.expected_result}"
            )

        return (
            f"Base URL: {input_data.base_url}\n"
            f"Framework: {input_data.framework}\n"
            f"Browsers: {', '.join(input_data.browsers)}\n"
            f"Viewport: {input_data.viewport['width']}x{input_data.viewport['height']}\n"
            f"Headless: {input_data.headless}\n"
            f"Timeout: {input_data.timeout} ms\n"
            "Manual test cases:\n"
            + "\n\n".join(cases_summary)
            + "\n\nReturn JSON with key 'tests': ["
              '{"filename": "...", "python_code": "...", "test_count": <int>}]. '
              "Each python_code must be valid pytest with Playwright page fixture."
        )

    def _parse_response(
        self, response: Dict[str, object], input_data: ManualToUITestsInput
    ) -> List[GeneratedTestFile]:
        tests = response.get("tests") if isinstance(response, dict) else None
        if not tests:
            return []

        files: List[GeneratedTestFile] = []
        for test in tests:
            try:
                filename = str(test.get("filename")) if isinstance(test, dict) else ""
                code = str(test.get("python_code")) if isinstance(test, dict) else ""
                if not filename:
                    filename = f"test_ui_{len(files) + 1}.py"
                if not code:
                    continue

                files.append(
                    GeneratedTestFile(
                        filename=self._sanitize_filename(filename),
                        test_file=code,
                        test_count=int(test.get("test_count", 1)),
                        framework=input_data.framework,
                        browsers=input_data.browsers,
                    )
                )
            except Exception as parse_error:
                self.log_error("Failed to parse LLM response item", parse_error)
                continue
        return files

    def _fallback_file(
        self, testcase: TestCaseDTO, input_data: ManualToUITestsInput
    ) -> GeneratedTestFile:
        slug = self._sanitize_filename(testcase.feature or "ui")
        filename = f"test_{slug}.py"
        code = self._build_stub(testcase, input_data)
        return GeneratedTestFile(
            filename=filename,
            test_file=code,
            test_count=1,
            framework=input_data.framework,
            browsers=input_data.browsers,
        )

    def _build_stub(
        self, testcase: TestCaseDTO, input_data: ManualToUITestsInput
    ) -> str:
        test_name = self._to_test_name(testcase.title)
        steps_code = "\n".join(
            f'        # Step {idx}: {step}'
            for idx, step in enumerate(testcase.steps or [], start=1)
        )
        if not steps_code:
            steps_code = "        # TODO: implement steps\n"

        return (
            "import allure\n"
            "import pytest\n"
            "from playwright.sync_api import Page, expect\n\n"
            f"@allure.feature('{testcase.feature}')\n"
            f"@allure.story('{testcase.story}')\n"
            f"@allure.title('{testcase.title}')\n"
            f"def {test_name}(page: Page):\n"
            f"    page.goto('{input_data.base_url}')\n"
            f"{steps_code}\n"
            "    # Add assertions with expect(...)\n"
        )

    def _sanitize_filename(self, value: str) -> str:
        import re

        clean = re.sub(r"[^\w\-\.]", "_", value.strip().lower())
        return clean or "test_ui"
