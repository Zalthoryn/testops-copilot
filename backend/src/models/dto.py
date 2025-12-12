"""
DTO models for TestOps Copilot
"""
from typing import List, Dict, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field

from .enums import TestPriority, TestType, JobStatus


class TestCaseDTO(BaseModel):
    """DTO для тест-кейса"""
    id: UUID = Field(default_factory=uuid4)
    title: str = Field(..., description="Название тест-кейса")
    feature: str = Field(..., description="Фича/функциональность")
    story: str = Field(..., description="User story")
    priority: TestPriority = Field(default=TestPriority.NORMAL, description="Приоритет тест-кейса")
    steps: List[str] = Field(default_factory=list, description="Шаги теста")
    expected_result: str = Field(..., description="Ожидаемый результат")
    python_code: str = Field(..., description="Python код теста (Allure TestOps)")
    test_type: TestType = Field(..., description="Тип теста")
    owner: str = Field(default="qa_team", description="Владелец теста")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class ManualUIGenerationRequest(BaseModel):
    """Запрос на генерацию ручных UI тест-кейсов"""
    project_name: Optional[str] = Field(default="UI Calculator Cloud.ru", description="Название проекта")
    requirements: str = Field(..., description="Требования")
    test_blocks: List[str] = Field(
        default=["main_page", "product_catalog", "configuration", "management", "mobile"],
        description="Блоки тестов"
    )
    target_count: int = Field(default=30, ge=1, le=100, description="Количество тест-кейсов")
    priority: TestPriority = Field(default=TestPriority.CRITICAL, description="Приоритет тест-кейсов")
    owner: Optional[str] = Field(default="qa_team", description="Владелец")
    include_screenshots: Optional[bool] = Field(default=True, description="Добавлять ли скриншоты")


class ManualAPIGenerationRequest(BaseModel):
    """Запрос на генерацию ручных API тест-кейсов"""
    openapi_url: Optional[str] = Field(None, description="URL OpenAPI спецификации")
    openapi_content: Optional[str] = Field(None, description="Контент OpenAPI спецификации")
    sections: List[str] = Field(
        default=["vms", "disks", "flavors"],
        description="Разделы API для генерации"
    )
    auth_type: Optional[str] = Field(default="bearer", description="Тип авторизации")
    target_count: int = Field(default=30, ge=1, le=100, description="Количество тест-кейсов")
    priority: Optional[TestPriority] = Field(default=TestPriority.NORMAL, description="Приоритет тест-кейсов")


class JobResponse(BaseModel):
    """Ответ на создание/получение job"""
    job_id: UUID = Field(..., description="ID задания")
    status: JobStatus = Field(..., description="Статус задания")
    message: Optional[str] = Field(None, description="Сообщение")
    estimated_time: Optional[int] = Field(None, description="Оценка времени в секундах")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    testcases: List[Any] = Field(default_factory=list, description="Сгенерированные тест-кейсы")
    download_url: Optional[str] = Field(None, description="Ссылка на скачивание")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Метрики")


class JobStatusResponse(JobResponse):
    """Расширенный ответ с состоянием job"""
    pass


class UIAutotestsRequest(BaseModel):
    """Запрос на генерацию UI автотестов"""
    manual_testcases_ids: List[UUID] = Field(..., description="ID ручных тест-кейсов для автотестов")
    framework: Optional[str] = Field(default="playwright", description="Фреймворк")
    browsers: Optional[List[str]] = Field(default=["chromium"], description="Браузеры")
    base_url: Optional[str] = Field(default="https://cloud.ru/calculator", description="Базовый URL")
    headless: Optional[bool] = Field(default=True, description="Запускать headless")
    priority_filter: Optional[List[str]] = Field(
        default=["CRITICAL", "NORMAL"],
        description="Фильтр по приоритетам"
    )


class APIAutotestsRequest(BaseModel):
    """Запрос на генерацию API автотестов"""
    manual_testcases_ids: List[UUID] = Field(..., description="ID ручных тест-кейсов для автотестов")
    openapi_url: Optional[str] = Field(None, description="URL OpenAPI спецификации")
    sections: List[str] = Field(
        default=["vms", "disks", "flavors"],
        description="Разделы API для генерации"
    )
    base_url: Optional[str] = Field(default="https://compute.api.cloud.ru", description="Базовый URL API")
    auth_token: Optional[str] = Field(None, description="Bearer токен")
    test_framework: Optional[str] = Field(default="pytest", description="Тестовый фреймворк")
    http_client: Optional[str] = Field(default="httpx", description="HTTP клиент")


class GitLabCommitRequest(BaseModel):
    """Payload для коммита/MR в GitLab"""
    testcases_job_id: UUID = Field(..., description="ID задания с тест-кейсами")
    repository: Optional[str] = Field(None, description="Путь repo owner/project (опционально, иначе из настроек)")
    branch: str = Field(default="main", description="Ветка для коммита")
    commit_message: str = Field(default="Add generated test cases", description="Сообщение коммита")
    create_mr: bool = Field(default=False, description="Создавать ли MR")
    target_branch: Optional[str] = Field(None, description="Целевая ветка MR")
    mr_title: Optional[str] = Field(None, description="Заголовок MR")
    mr_description: Optional[str] = Field(None, description="Описание MR")


class StandardsCheckRequest(BaseModel):
    """Запрос на проверку стандартов"""
    files: List[Dict[str, str]] = Field(..., description="Файлы для проверки")
    checks: List[str] = Field(
        default=["aaa", "allure", "naming"],
        description="Набор проверок"
    )


class StandardsViolation(BaseModel):
    """Нарушение стандартов"""
    file: str = Field(..., description="Файл")
    line: int = Field(..., description="Строка")
    severity: str = Field(..., description="Уровень (error, warning, info)")
    rule: str = Field(..., description="Правило")
    message: str = Field(..., description="Описание")
    suggested_fix: str = Field(..., description="Предлагаемое исправление")


class StandardsReport(BaseModel):
    """Отчет о проверке стандартов"""
    job_id: UUID = Field(..., description="ID задания")
    status: JobStatus = Field(..., description="Статус")
    total_files: int = Field(..., description="Кол-во файлов")
    total_violations: int = Field(..., description="Кол-во нарушений")
    violations_by_severity: Dict[str, int] = Field(
        default_factory=dict,
        description="Нарушения по уровням"
    )
    violations: List[StandardsViolation] = Field(
        default_factory=list,
        description="Нарушения"
    )
    generated_at: datetime = Field(default_factory=datetime.now)


class OptimizationRequest(BaseModel):
    """Запрос на оптимизацию тестов"""
    repository_url: Optional[str] = Field(None, description="URL репозитория")
    test_files: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Файлы тестов")
    requirements: Optional[str] = Field(None, description="Требования")
    checks: List[str] = Field(
        default=["duplicates", "coverage", "outdated"],
        description="Проверки оптимизации"
    )
    optimization_level: Optional[str] = Field(default="moderate", description="Уровень оптимизации")


class OptimizationResult(BaseModel):
    """Результат оптимизации"""
    job_id: UUID = Field(..., description="ID задания")
    status: JobStatus = Field(..., description="Статус")
    analysis: Dict[str, Any] = Field(default_factory=dict, description="Аналитика")
    recommendations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Рекомендации"
    )
    optimized_testcases: List[TestCaseDTO] = Field(
        default_factory=list,
        description="Оптимизированные тест-кейсы"
    )
    generated_at: datetime = Field(default_factory=datetime.now)


class ComputeValidationRequest(BaseModel):
    """Запрос на проверку подключения к Compute API"""
    token: Optional[str] = Field(None, description="Bearer токен")
    key_id: Optional[str] = Field(None, description="Key ID")
    secret: Optional[str] = Field(None, description="Secret")


class ComputeValidationResponse(BaseModel):
    """Ответ о проверке Compute API"""
    valid: bool = Field(..., description="Валиден ли доступ")
    endpoint: str = Field(..., description="Endpoint API")
    available_resources: List[str] = Field(default_factory=list, description="Доступные ресурсы")
    error: Optional[str] = Field(None, description="Ошибка")


class ConfigResponse(BaseModel):
    """Ответ с конфигурацией"""
    llm_model: str = Field(..., description="LLM модель")
    compute_endpoint: str = Field(..., description="Endpoint Compute API")
    gitlab_configured: bool = Field(..., description="GitLab настроен")
    llm_available: bool = Field(..., description="Доступен ли LLM")
    compute_available: bool = Field(..., description="Доступен ли Compute API")
    environment: str = Field(..., description="Среда (development/production)")


class HealthResponse(BaseModel):
    """Ответ healthcheck"""
    status: str = Field(..., description="Состояние")
    llm_available: bool = Field(..., description="LLM доступен")
    compute_api_available: bool = Field(..., description="Compute API доступен")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0", description="Версия сервиса")
