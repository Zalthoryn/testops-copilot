"""
Agent for lightweight static checks against AAA and Allure conventions.
"""
import ast
import re
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.models.dto import StandardsReport, StandardsViolation
from src.models.enums import Severity
from src.services.llm_client import LLMClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StandardsCheckInput(AgentInput):
    """Input for standards verification."""

    files: List[Dict[str, str]] = Field(..., description="List of files with content")
    checks: List[str] = Field(
        default_factory=lambda: ["aaa", "allure", "naming"],
        description="Rules to apply",
    )


class StandardsCheckOutput(AgentOutput):
    """Result of standards validation."""

    report: Optional[StandardsReport] = None
    total_files: int = 0
    total_violations: int = 0


class StandardsAgent(BaseAgent[StandardsCheckInput, StandardsCheckOutput]):
    """Run quick static checks for AAA pattern, Allure decorators, and naming."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)
        self.available_checks = {
            "aaa": self._check_aaa,
            "allure": self._check_allure,
            "naming": self._check_naming,
        }

    def get_system_prompt(self) -> str:
        return (
            "You are a code reviewer focusing on test standards (AAA, Allure, naming). "
            "Summaries are optional; main output is provided by the application."
        )

    async def execute(
        self, input_data: StandardsCheckInput
    ) -> StandardsCheckOutput:
        self.log_progress("Starting standards validation")
        try:
            violations: List[StandardsViolation] = []

            for file_info in input_data.files:
                filename = file_info.get("filename", "unknown")
                content = file_info.get("content", "")
                for check_name in input_data.checks:
                    checker = self.available_checks.get(check_name)
                    if checker:
                        violations.extend(checker(filename, content))

            report = self._build_report(
                input_data.job_id, len(input_data.files), violations
            )

            return StandardsCheckOutput(
                success=True,
                report=report,
                total_files=len(input_data.files),
                total_violations=len(violations),
            )
        except Exception as exc:
            self.log_error("Standards check failed", exc)
            return StandardsCheckOutput(
                success=False,
                error=str(exc),
                report=None,
                total_files=len(input_data.files),
                total_violations=0,
            )

    def _check_aaa(self, filename: str, content: str) -> List[StandardsViolation]:
        violations: List[StandardsViolation] = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(node))
                    if not has_assert:
                        violations.append(
                            StandardsViolation(
                                file=filename,
                                line=node.lineno,
                                severity=Severity.ERROR.value,
                                rule="AAA_pattern",
                                message="Test lacks assertions (Assert stage missing)",
                                suggested_fix="Add at least one assert statement",
                            )
                        )
        except SyntaxError:
            violations.append(
                StandardsViolation(
                    file=filename,
                    line=1,
                    severity=Severity.ERROR.value,
                    rule="syntax",
                    message="File has syntax errors",
                    suggested_fix="Fix Python syntax before running tests",
                )
            )
        return violations

    def _check_allure(self, filename: str, content: str) -> List[StandardsViolation]:
        violations: List[StandardsViolation] = []
        has_import = "import allure" in content or "from allure" in content

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            if re.match(r"^def\s+test_", line.strip()):
                window = "\n".join(lines[max(0, idx - 4) : idx])
                if "@allure" not in window:
                    violations.append(
                        StandardsViolation(
                            file=filename,
                            line=idx,
                            severity=Severity.WARNING.value,
                            rule="allure_decorator",
                            message="Test is missing Allure decorators",
                            suggested_fix="Add @allure.feature/story/title before the test",
                        )
                    )

        if not has_import:
            violations.append(
                StandardsViolation(
                    file=filename,
                    line=1,
                    severity=Severity.ERROR.value,
                    rule="allure_import",
                    message="Allure import not found",
                    suggested_fix="Add 'import allure' to the file",
                )
            )
        return violations

    def _check_naming(self, filename: str, content: str) -> List[StandardsViolation]:
        violations: List[StandardsViolation] = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    if not re.match(r"^test_[a-z0-9_]+$", node.name):
                        violations.append(
                            StandardsViolation(
                                file=filename,
                                line=node.lineno,
                                severity=Severity.WARNING.value,
                                rule="naming_test",
                                message="Test name should use snake_case after test_",
                                suggested_fix="Rename to snake_case: test_example_case",
                            )
                        )
        except SyntaxError:
            return violations
        return violations

    def _build_report(
        self, job_id: UUID, total_files: int, violations: List[StandardsViolation]
    ) -> StandardsReport:
        counts = {"error": 0, "warning": 0, "info": 0}
        for v in violations:
            if v.severity in counts:
                counts[v.severity] += 1

        status = "completed" if counts["error"] == 0 else "failed"
        return StandardsReport(
            job_id=job_id,
            status=status,
            total_files=total_files,
            total_violations=len(violations),
            violations_by_severity=counts,
            violations=violations,
            generated_at=None,
        )
