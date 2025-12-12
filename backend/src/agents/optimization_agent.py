"""
Agent for lightweight optimization analysis of existing test cases.
"""
from difflib import SequenceMatcher
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from src.agents.base_agent import AgentInput, AgentOutput, BaseAgent
from src.models.dto import TestCaseDTO
from src.models.enums import TestPriority
from src.services.llm_client import LLMClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OptimizationInput(AgentInput):
    """Input for optimization analysis."""

    testcases: List[TestCaseDTO] = Field(default_factory=list)
    requirements_text: Optional[str] = Field(default=None)
    checks: List[str] = Field(
        default_factory=lambda: ["duplicates", "coverage", "outdated"]
    )
    similarity_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class OptimizationOutput(AgentOutput):
    """Result of optimization analysis."""

    analysis: Dict[str, object] = Field(default_factory=dict)
    recommendations: List[Dict[str, object]] = Field(default_factory=list)
    optimized_testcases: List[TestCaseDTO] = Field(default_factory=list)


class OptimizationAgent(BaseAgent[OptimizationInput, OptimizationOutput]):
    """Detect duplicates, coverage gaps, and outdated tests."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)

    def get_system_prompt(self) -> str:
        return (
            "You are a QA lead analyzing test suites for redundancy and gaps. "
            "The application will handle the final formatting."
        )

    async def execute(
        self, input_data: OptimizationInput
    ) -> OptimizationOutput:
        self.log_progress("Starting optimization analysis")
        try:
            analysis: Dict[str, object] = {}
            recommendations: List[Dict[str, object]] = []

            if "duplicates" in input_data.checks:
                dup_result = self._find_duplicates(
                    input_data.testcases, input_data.similarity_threshold
                )
                analysis["duplicates"] = dup_result
                recommendations.extend(dup_result["recommendations"])

            if "coverage" in input_data.checks and input_data.requirements_text:
                cov_result = self._check_coverage(
                    input_data.testcases, input_data.requirements_text
                )
                analysis["coverage"] = cov_result
                recommendations.extend(cov_result["recommendations"])

            if "outdated" in input_data.checks:
                outdated_result = self._flag_outdated(input_data.testcases)
                analysis["outdated"] = outdated_result
                recommendations.extend(outdated_result["recommendations"])

            optimized = input_data.testcases  # Placeholder; no mutations applied yet

            return OptimizationOutput(
                success=True,
                analysis=analysis,
                recommendations=recommendations,
                optimized_testcases=optimized,
            )
        except Exception as exc:
            self.log_error("Optimization failed", exc)
            return OptimizationOutput(
                success=False,
                error=str(exc),
                analysis={},
                recommendations=[],
                optimized_testcases=[],
            )

    def _find_duplicates(
        self, testcases: List[TestCaseDTO], threshold: float
    ) -> Dict[str, object]:
        duplicates: List[Dict[str, object]] = []
        recommendations: List[Dict[str, object]] = []

        for idx, tc in enumerate(testcases):
            for other in testcases[idx + 1 :]:
                score = self._similarity(tc, other)
                if score >= threshold:
                    duplicates.append(
                        {
                            "testcase1": str(tc.id),
                            "testcase2": str(other.id),
                            "similarity": score,
                        }
                    )
                    keep = tc if tc.priority.value >= other.priority.value else other
                    drop = other if keep is tc else tc
                    recommendations.append(
                        {
                            "type": "duplicate",
                            "severity": "medium",
                            "message": f"Tests {tc.title} and {other.title} look similar ({score:.2f})",
                            "action": f"Keep {keep.title}, review {drop.title} for merge/removal",
                        }
                    )

        return {
            "duplicates": duplicates,
            "threshold_used": threshold,
            "recommendations": recommendations,
        }

    def _check_coverage(
        self, testcases: List[TestCaseDTO], requirements_text: str
    ) -> Dict[str, object]:
        requirements = [
            line.strip()
            for line in requirements_text.splitlines()
            if line.strip() and len(line.strip()) > 8
        ][:50]
        coverage: List[Dict[str, object]] = []
        recommendations: List[Dict[str, object]] = []

        for req in requirements:
            covered_by = [
                str(tc.id)
                for tc in testcases
                if self._covers_requirement(tc, req)
            ]
            coverage.append(
                {
                    "requirement": req,
                    "covered": bool(covered_by),
                    "testcases": covered_by,
                }
            )
            if not covered_by:
                recommendations.append(
                    {
                        "type": "coverage",
                        "severity": "high",
                        "message": f"Requirement not covered: {req[:80]}",
                        "action": "Create test case for this requirement",
                    }
                )

        percent = (
            sum(1 for item in coverage if item["covered"]) / len(coverage) * 100
            if coverage
            else 0
        )
        return {
            "coverage": coverage,
            "coverage_percent": percent,
            "recommendations": recommendations,
        }

    def _flag_outdated(self, testcases: List[TestCaseDTO]) -> Dict[str, object]:
        outdated: List[Dict[str, object]] = []
        recommendations: List[Dict[str, object]] = []

        for tc in testcases:
            reasons: List[str] = []
            if tc.priority == TestPriority.LOW:
                reasons.append("Low priority test; consider review")
            if tc.updated_at is None:
                reasons.append("Never updated")

            if reasons:
                outdated.append({"id": str(tc.id), "title": tc.title, "reasons": reasons})
                recommendations.append(
                    {
                        "type": "outdated",
                        "severity": "medium",
                        "message": f"{tc.title} may be outdated",
                        "action": "; ".join(reasons),
                    }
                )

        return {"outdated": outdated, "recommendations": recommendations}

    def _similarity(self, first: TestCaseDTO, second: TestCaseDTO) -> float:
        title_score = SequenceMatcher(
            None, first.title.lower(), second.title.lower()
        ).ratio()
        steps_score = SequenceMatcher(
            None, " ".join(first.steps).lower(), " ".join(second.steps).lower()
        ).ratio()
        return (title_score * 0.6) + (steps_score * 0.4)

    def _covers_requirement(self, testcase: TestCaseDTO, requirement: str) -> bool:
        text = " ".join([testcase.title, testcase.story, " ".join(testcase.steps)])
        return requirement.lower() in text.lower()
