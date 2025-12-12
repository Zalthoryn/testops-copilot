"""
Агент для генерации ручных UI тест-кейсов из требований
"""
from typing import List, Optional
from uuid import UUID
from pydantic import Field

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.models.dto import TestCaseDTO
from src.models.enums import TestPriority, TestType
from src.services.llm_client import LLMClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RequirementsToManualTCInput(AgentInput):
    """Входные данные для агента генерации ручных UI тест-кейсов"""
    requirements: str = Field(..., description="Текст требований")
    test_blocks: List[str] = Field(default=["main_page", "product_catalog", "configuration"])
    target_count: int = Field(default=30)
    priority: TestPriority = Field(default=TestPriority.NORMAL)
    owner: str = Field(default="qa_team")
    project_name: str = Field(default="UI Calculator")


class RequirementsToManualTCOutput(AgentOutput):
    """Выходные данные агента"""
    testcases: List[TestCaseDTO] = Field(default_factory=list)
    total_generated: int = 0


class RequirementsToManualTCAgent(BaseAgent[RequirementsToManualTCInput, RequirementsToManualTCOutput]):
    """
    Агент для генерации ручных UI тест-кейсов на основе требований.
    Генерирует тест-кейсы в формате Allure TestOps.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(llm_client)

    def get_system_prompt(self) -> str:
        return """Ты - опытный QA инженер, специализирующийся на создании ручных UI тест-кейсов.

Твоя задача - анализировать требования и создавать детальные тест-кейсы в формате Allure TestOps.

Каждый тест-кейс должен включать:
1. Четкое название (title)
2. Feature (функциональная область)
3. Story (пользовательская история)
4. Пошаговые инструкции (steps)
5. Ожидаемый результат (expected_result)
6. Python код в формате Allure с декоратором @allure.manual

Важные правила:
- Тест-кейсы должны быть атомарными
- Шаги должны быть конкретными и проверяемыми
- Используй паттерн AAA (Arrange, Act, Assert) в структуре шагов
- Каждый тест должен проверять одну конкретную функциональность

Отвечай в формате JSON:
{
  "testcases": [
    {
      "title": "...",
      "feature": "...",
      "story": "...",
      "steps": ["...", "..."],
      "expected_result": "..."
    }
  ]
}"""

    async def execute(self, input_data: RequirementsToManualTCInput) -> RequirementsToManualTCOutput:
        """Генерация ручных UI тест-кейсов"""
        self.log_progress(f"Starting testcase generation for {len(input_data.test_blocks)} blocks")

        try:
            testcases = []

            # Генерируем тест-кейсы для каждого блока
            for block in input_data.test_blocks:
                self.log_progress(f"Generating testcases for block: {block}")

                prompt = f"""Проанализируй следующие требования и создай ручные UI тест-кейсы для блока "{block}".

Требования:
{input_data.requirements}

Создай {input_data.target_count // len(input_data.test_blocks)} тест-кейсов для этого блока.
Приоритет тест-кейсов: {input_data.priority.value}

Формат ответа - JSON со списком тест-кейсов."""

                try:
                    response = await self.generate_structured_response(prompt)

                    if "testcases" in response:
                        for tc_data in response["testcases"]:
                            # Генерируем Allure код
                            python_code = self.generate_allure_code(
                                feature=tc_data.get("feature", f"UI {block.replace('_', ' ').title()}"),
                                story=tc_data.get("story", block),
                                title=tc_data["title"],
                                steps=tc_data.get("steps", []),
                                test_type=TestType.MANUAL_UI,
                                is_manual=True
                            )

                            testcase = self.create_testcase(
                                title=tc_data["title"],
                                feature=tc_data.get("feature", f"UI {block.replace('_', ' ').title()}"),
                                story=tc_data.get("story", block),
                                steps=tc_data.get("steps", []),
                                expected_result=tc_data.get("expected_result", "Функциональность работает корректно"),
                                python_code=python_code,
                                test_type=TestType.MANUAL_UI,
                                priority=input_data.priority,
                                owner=input_data.owner
                            )
                            testcases.append(testcase)

                except Exception as e:
                    self.log_error(f"Error generating testcases for block {block}", e)
                    continue

            self.log_progress(f"Generated {len(testcases)} testcases total")

            return RequirementsToManualTCOutput(
                success=True,
                testcases=testcases,
                total_generated=len(testcases)
            )

        except Exception as e:
            self.log_error("Failed to generate testcases", e)
            return RequirementsToManualTCOutput(
                success=False,
                error=str(e),
                testcases=[],
                total_generated=0
            )
