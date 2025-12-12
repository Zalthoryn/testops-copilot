# backend/src/api/v1/router.py
"""
Роутер для API v1
"""
from fastapi import APIRouter

from src.api.v1.endpoints import (
    testcases,
    autotests,
    standards,
    optimization,
    integrations,
    config
)

api_router = APIRouter()

# Подключаем все роутеры endpoints
api_router.include_router(testcases.router)
api_router.include_router(autotests.router)
api_router.include_router(standards.router)
api_router.include_router(optimization.router)
api_router.include_router(integrations.router)
api_router.include_router(config.router)