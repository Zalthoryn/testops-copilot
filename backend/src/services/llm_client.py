"""
LLM Client для работы с Cloud.ru LLM API (OpenAI-совместимый)
На основе примера request_to_model_example.py
"""
import json
import re
from typing import Dict, Any, Optional, List
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils.logger import get_logger
from src.utils.exceptions import LLMException

logger = get_logger(__name__)


class LLMClient:
    """
    Клиент для работы с LLM API Cloud.ru
    Использует OpenAI-совместимый API (синхронный клиент в async контексте)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Инициализация LLM клиента

        Args:
            api_key: API ключ (по умолчанию из настроек)
            base_url: Базовый URL API (по умолчанию из настроек)
            model: Модель для использования (по умолчанию из настроек)
        """
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url or settings.LLM_BASE_URL
        self.model = model or settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout = settings.LLM_TIMEOUT

        # Статистика
        self._call_count = 0
        self._failed_calls = 0

        if not self.api_key:
            logger.warning("LLM API key not set. LLM features will not work.")
            self.client = None
        else:
            # Инициализация OpenAI клиента с Cloud.ru endpoint
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout
            )
            logger.info(f"LLM client initialized: model={self.model}, base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Генерация текста с помощью LLM

        Args:
            prompt: Пользовательский промпт
            system_prompt: Системный промпт
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов

        Returns:
            Сгенерированный текст
        """
        if not self.client:
            raise LLMException("LLM client not initialized. API key is missing.")

        self._call_count += 1

        try:
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            logger.debug(f"LLM request #{self._call_count}: {len(prompt)} chars")

            # Вызов API согласно примеру request_to_model_example.py
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                presence_penalty=0,
                top_p=0.95
            )

            result = response.choices[0].message.content
            logger.debug(f"LLM response: {len(result)} chars")

            return result

        except Exception as e:
            self._failed_calls += 1
            logger.error(f"LLM generation error: {e}")
            raise LLMException(f"Failed to generate response: {str(e)}")

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 3000
    ) -> str:
        """
        Генерация структурированного ответа

        Args:
            system_prompt: Системный промпт
            user_prompt: Пользовательский промпт
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
        """
        return await self.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Генерация JSON ответа

        Args:
            prompt: Пользовательский промпт
            system_prompt: Системный промпт
            temperature: Температура генерации

        Returns:
            Parsed JSON response
        """
        # Добавляем инструкцию для JSON
        json_system = (system_prompt or "") + "\n\nОтвечай только валидным JSON без дополнительного текста."

        response = await self.generate(
            prompt=prompt,
            system_prompt=json_system,
            temperature=temperature if temperature is not None else 0.3
        )

        # Извлекаем JSON из ответа
        try:
            json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', response)
            if json_match:
                return json.loads(json_match.group())
            else:
                return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            raise LLMException(f"Invalid JSON response from LLM: {str(e)}")

    async def generate_with_context(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Генерация с полным контекстом сообщений

        Args:
            messages: Список сообщений [{"role": "...", "content": "..."}]
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
        """
        if not self.client:
            raise LLMException("LLM client not initialized. API key is missing.")

        self._call_count += 1

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                presence_penalty=0,
                top_p=0.95
            )

            return response.choices[0].message.content

        except Exception as e:
            self._failed_calls += 1
            logger.error(f"LLM generation error: {e}")
            raise LLMException(f"Failed to generate response: {str(e)}")

    def is_available(self) -> bool:
        """Проверка доступности клиента"""
        return self.client is not None

    async def validate_connection(self) -> bool:
        """Проверка соединения с LLM API"""
        if not self.client:
            return False

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.warning(f"LLM connection validation failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья LLM сервиса"""
        if not self.client:
            return {
                "status": "unavailable",
                "connected": False,
                "error": "API key not configured"
            }

        try:
            is_connected = await self.validate_connection()
            return {
                "status": "healthy" if is_connected else "degraded",
                "connected": is_connected,
                "model": self.model,
                "base_url": self.base_url,
                "statistics": self.get_statistics()
            }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "error": str(e)
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики использования"""
        return {
            "total_calls": self._call_count,
            "failed_calls": self._failed_calls,
            "success_rate": ((self._call_count - self._failed_calls) / self._call_count * 100)
                            if self._call_count > 0 else 0
        }

    async def close(self):
        """Закрытие клиента"""
        pass


# Глобальный экземпляр LLM клиента
_global_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Получение глобального экземпляра LLM клиента (singleton)

    Returns:
        Экземпляр LLMClient
    """
    global _global_llm_client
    if _global_llm_client is None:
        _global_llm_client = LLMClient()
    return _global_llm_client


async def close_llm_client():
    """Закрытие глобального LLM клиента"""
    global _global_llm_client
    if _global_llm_client:
        await _global_llm_client.close()
        _global_llm_client = None
