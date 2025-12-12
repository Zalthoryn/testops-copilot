"""
Фабрика для создания агентов TestOps Copilot
"""
from typing import Dict, Type, Optional

from src.services.llm_client import LLMClient, get_llm_client
from src.agents.base_agent import BaseAgent
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentFactory:
    """Фабрика для создания и управления агентами"""

    _agent_registry: Dict[str, Type[BaseAgent]] = {}

    @classmethod
    def register_agent(cls, agent_name: str, agent_class: Type[BaseAgent]):
        """Регистрация агента в фабрике"""
        cls._agent_registry[agent_name] = agent_class
        logger.debug(f"Registered agent: {agent_name}")

    @classmethod
    def create_agent(
        cls,
        agent_name: str,
        llm_client: Optional[LLMClient] = None
    ) -> BaseAgent:
        """
        Создание экземпляра агента

        Args:
            agent_name: Имя агента
            llm_client: Клиент LLM (если None, используется глобальный)

        Returns:
            Экземпляр агента
        """
        if agent_name not in cls._agent_registry:
            raise ValueError(f"Agent '{agent_name}' not found in registry")

        agent_class = cls._agent_registry[agent_name]
        return agent_class(llm_client=llm_client or get_llm_client())

    @classmethod
    def get_available_agents(cls) -> Dict[str, Type[BaseAgent]]:
        """Получение списка доступных агентов"""
        return cls._agent_registry.copy()

    @classmethod
    def is_agent_registered(cls, agent_name: str) -> bool:
        """Проверка регистрации агента"""
        return agent_name in cls._agent_registry


def register_all_agents():
    """Регистрация всех агентов в фабрике"""
    # Отложенный импорт для избежания циклических зависимостей
    from src.agents.requirements_to_manual_tc import RequirementsToManualTCAgent
    from src.agents.openapi_to_api_tc import OpenAPIToAPITCAgent
    from src.agents.manual_to_ui_tests import ManualToUITestsAgent
    from src.agents.openapi_to_api_tests import OpenAPIToAPITestsAgent
    from src.agents.standards_agent import StandardsAgent
    from src.agents.optimization_agent import OptimizationAgent

    AgentFactory.register_agent("requirements_to_manual_tc", RequirementsToManualTCAgent)
    AgentFactory.register_agent("openapi_to_api_tc", OpenAPIToAPITCAgent)
    AgentFactory.register_agent("manual_to_ui_tests", ManualToUITestsAgent)
    AgentFactory.register_agent("openapi_to_api_tests", OpenAPIToAPITestsAgent)
    AgentFactory.register_agent("standards_check", StandardsAgent)
    AgentFactory.register_agent("optimization", OptimizationAgent)

    logger.info(f"Registered {len(AgentFactory.get_available_agents())} agents")


# Автоматическая регистрация при импорте (если агенты доступны)
try:
    register_all_agents()
except ImportError as e:
    logger.warning(f"Some agents could not be registered: {e}")
