# backend/src/models/enums.py
"""
Перечисления для TestOps Copilot
"""
from enum import Enum


class TestPriority(str, Enum):
    """Приоритет тест-кейса"""
    CRITICAL = "CRITICAL"
    NORMAL = "NORMAL"
    LOW = "LOW"
    
    def __str__(self):
        return self.value


class TestType(str, Enum):
    """Тип теста"""
    MANUAL_UI = "manual_ui"
    MANUAL_API = "manual_api"
    AUTOMATED_UI = "automated_ui"
    AUTOMATED_API = "automated_api"
    
    def __str__(self):
        return self.value


class JobStatus(str, Enum):
    """Статус задания"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    
    def __str__(self):
        return self.value


class Framework(str, Enum):
    """Фреймворки для тестирования"""
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    PYTEST = "pytest"
    UNITTEST = "unittest"
    TESTNG = "testng"
    
    def __str__(self):
        return self.value


class HttpClient(str, Enum):
    """HTTP клиенты"""
    HTTPX = "httpx"
    REQUESTS = "requests"
    AIOHTTP = "aiohttp"
    
    def __str__(self):
        return self.value


class Severity(str, Enum):
    """Серьезность нарушения"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    
    def __str__(self):
        return self.value


class OptimizationLevel(str, Enum):
    """Уровень оптимизации"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    
    def __str__(self):
        return self.value