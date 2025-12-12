"""
Базовый класс для всех агентов TestOps Copilot
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from src.services.llm_client import LLMClient, get_llm_client
from src.models.dto import TestCaseDTO
from src.models.enums import TestPriority, TestType
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentInput(BaseModel):
    """Базовый класс для входных данных агента"""
    job_id: UUID

    class Config:
        arbitrary_types_allowed = True


class AgentOutput(BaseModel):
    """Базовый класс для выходных данных агента"""
    success: bool = True
    error: Optional[str] = None
    generated_at: datetime = None

    def __init__(self, **data):
        if 'generated_at' not in data or data['generated_at'] is None:
            data['generated_at'] = datetime.now()
        super().__init__(**data)

    class Config:
        arbitrary_types_allowed = True


InputT = TypeVar('InputT', bound=AgentInput)
OutputT = TypeVar('OutputT', bound=AgentOutput)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Базовый класс агента для генерации тест-кейсов.
    Все специализированные агенты должны наследоваться от этого класса.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Инициализация агента

        Args:
            llm_client: Клиент для работы с LLM (если None, используется глобальный)
        """
        self.llm_client = llm_client or get_llm_client()
        self.name = self.__class__.__name__
        logger.info(f"Initialized agent: {self.name}")

    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """
        Выполнение основной логики агента

        Args:
            input_data: Входные данные

        Returns:
            Результат выполнения
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Получение системного промпта для агента

        Returns:
            Системный промпт
        """
        pass

    async def generate_with_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        Генерация ответа с помощью LLM

        Args:
            prompt: Пользовательский промпт
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            Сгенерированный текст
        """
        system_prompt = self.get_system_prompt()
        return await self.llm_client.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

    async def generate_structured_response(
        self,
        prompt: str,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Генерация структурированного JSON ответа

        Args:
            prompt: Промпт для генерации
            temperature: Температура генерации

        Returns:
            Parsed JSON response
        """
        system_prompt = self.get_system_prompt()
        return await self.llm_client.generate_json(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature
        )

    def create_testcase(
        self,
        title: str,
        feature: str,
        story: str,
        steps: List[str],
        expected_result: str,
        python_code: str,
        test_type: TestType,
        priority: TestPriority = TestPriority.NORMAL,
        owner: str = "qa_team"
    ) -> TestCaseDTO:
        """
        Создание тест-кейса

        Args:
            title: Название тест-кейса
            feature: Функциональная область
            story: Пользовательская история
            steps: Шаги выполнения
            expected_result: Ожидаемый результат
            python_code: Python код тест-кейса
            test_type: Тип теста
            priority: Приоритет
            owner: Владелец

        Returns:
            Объект TestCaseDTO
        """
        return TestCaseDTO(
            title=title,
            feature=feature,
            story=story,
            steps=steps,
            expected_result=expected_result,
            python_code=python_code,
            test_type=test_type,
            priority=priority,
            owner=owner
        )

    def generate_allure_code(
        self,
        feature: str,
        story: str,
        title: str,
        steps: List[str],
        test_type: TestType,
        is_manual: bool = True
    ) -> str:
        """
        Генерация Python кода для тест-кейса в формате Allure

        Args:
            feature: Функциональная область
            story: Пользовательская история
            title: Название тест-кейса
            steps: Шаги выполнения
            test_type: Тип теста
            is_manual: Является ли тест ручным

        Returns:
            Python код в формате Allure
        """
        # Формируем имя класса и теста
        class_name = self._to_class_name(feature)
        test_name = self._to_test_name(title)

        # Генерируем шаги
        steps_code = ""
        for i, step in enumerate(steps, 1):
            steps_code += f'        with allure.step("{step}"):\n'
            steps_code += f'            pass  # Step {i}\n'

        # Определяем декоратор
        manual_decorator = "@allure.manual\n    " if is_manual else ""

        code = f'''import allure
import pytest

@allure.feature("{feature}")
@allure.story("{story}")
class Test{class_name}:
    """Тест-кейсы для {feature}"""

    {manual_decorator}@allure.title("{title}")
    def {test_name}(self):
        """
        {title}
        """
{steps_code}
'''
        return code

    def _to_class_name(self, text: str) -> str:
        """Преобразование текста в имя класса"""
        words = text.replace("-", " ").replace("_", " ").split()
        return "".join(word.capitalize() for word in words)

    def _to_test_name(self, text: str) -> str:
        """Преобразование текста в имя теста"""
        import re
        # Убираем специальные символы и заменяем пробелы на подчеркивания
        clean = re.sub(r'[^\w\s]', '', text.lower())
        words = clean.split()
        return "test_" + "_".join(words[:6])  # Ограничиваем длину

    def log_progress(self, message: str):
        """Логирование прогресса выполнения"""
        logger.info(f"[{self.name}] {message}")

    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Логирование ошибки"""
        if exception:
            logger.error(f"[{self.name}] {message}: {exception}")
        else:
            logger.error(f"[{self.name}] {message}")
