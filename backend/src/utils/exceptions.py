# backend/src/utils/exceptions.py
"""
Пользовательские исключения для TestOps Copilot
"""


class TestOpsException(Exception):
    """Базовое исключение для TestOps Copilot"""
    
    def __init__(self, message: str, detail: str = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class LLMException(TestOpsException):
    """Ошибка при работе с LLM"""
    pass


class ComputeAPIException(TestOpsException):
    """Ошибка при работе с Evolution Compute API"""
    pass


class AuthenticationException(TestOpsException):
    """Ошибка аутентификации"""
    pass


class OpenAPIException(TestOpsException):
    """Ошибка парсинга OpenAPI спецификации"""
    pass


class TestCaseGenerationException(TestOpsException):
    """Ошибка генерации тест-кейсов"""
    pass


class ValidationException(TestOpsException):
    """Ошибка валидации"""
    pass


class JobNotFoundException(TestOpsException):
    """Задание не найдено"""
    pass


class GitLabException(TestOpsException):
    """Ошибка интеграции с GitLab"""
    pass


class StorageException(TestOpsException):
    """Ошибка хранилища"""
    pass


class RateLimitException(TestOpsException):
    """Превышен лимит запросов"""
    pass

class AgentException(TestOpsException):
    """Ошибка агента"""
    pass
