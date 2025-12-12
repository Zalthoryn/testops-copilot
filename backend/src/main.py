"""
TestOps Copilot - Главный модуль приложения
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from src.config import settings
from src.api.v1.router import api_router
from src.utils.logger import get_logger, setup_logging
from src.utils.exceptions import TestOpsException
from src.services.llm_client import LLMClient

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    logger.info("Starting TestOps Copilot backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")
    logger.info(f"LLM Base URL: {settings.LLM_BASE_URL}")
    logger.info(f"Compute API: {settings.COMPUTE_API_URL}")

    # Инициализация LLM клиента
    if settings.LLM_API_KEY:
        try:
            llm_client = LLMClient()
            app.state.llm_client = llm_client
            app.state.llm_available = True
            logger.info("LLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
            app.state.llm_client = None
            app.state.llm_available = False
    else:
        logger.warning("LLM API key not set. LLM features will not work.")
        app.state.llm_client = None
        app.state.llm_available = False

    yield

    # Shutdown
    logger.info("Shutting down TestOps Copilot backend...")
    logger.info("Shutdown complete")


def create_application() -> FastAPI:
    """Создание экземпляра FastAPI приложения"""
    application = FastAPI(
        title="TestOps Copilot API",
        description="AI-powered система для автоматизации QA процессов",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )

    # Настройка CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключение роутеров
    application.include_router(api_router, prefix="/api")

    # Кастомная обработка исключений
    @application.exception_handler(TestOpsException)
    async def testops_exception_handler(request, exc):
        logger.error(f"TestOpsException: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "error": exc.__class__.__name__,
                "message": str(exc),
                "detail": getattr(exc, "detail", None)
            }
        )

    @application.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "Внутренняя ошибка сервера",
                "detail": str(exc) if settings.ENVIRONMENT == "development" else None
            }
        )

    # Swagger UI
    @application.get("/docs", include_in_schema=False)
    @application.get("/api/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url="/api/openapi.json",
            title="TestOps Copilot API - Swagger UI",
            swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
            swagger_css_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css",
        )

    # Root endpoint
    @application.get("/", include_in_schema=False)
    async def root():
        return {
            "name": "TestOps Copilot",
            "version": "1.0.0",
            "description": "AI-powered система для автоматизации QA процессов",
            "docs": "/docs",
            "health": "/health"
        }

    # Healthcheck endpoint
    @application.get("/health", tags=["health"])
    async def health_check():
        llm_available = getattr(application.state, 'llm_available', False)
        compute_available = bool(settings.COMPUTE_API_TOKEN)

        status = "healthy" if llm_available else "degraded"

        return {
            "status": status,
            "environment": settings.ENVIRONMENT,
            "llm_available": llm_available,
            "compute_api_available": compute_available,
            "llm_model": settings.LLM_MODEL
        }

    # Кастомная OpenAPI схема
    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema

        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )

        openapi_schema["tags"] = [
            {"name": "testcases", "description": "Генерация тест-кейсов"},
            {"name": "autotests", "description": "Генерация автотестов"},
            {"name": "standards", "description": "Проверка стандартов"},
            {"name": "optimization", "description": "Оптимизация тестов"},
            {"name": "config", "description": "Настройки системы"},
            {"name": "health", "description": "Проверка состояния системы"}
        ]

        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi

    return application


# Создание приложения
app = create_application()

# Настройка логирования
setup_logging(settings.LOG_LEVEL)
