# TestOps Copilot

AI-помощник для QA: генерация тест-кейсов, автотестов, проверка стандартов и оптимизация набора тестов. Стек: FastAPI (Python) + React/Vite (TS), Redis зарезервирован под фоновые задачи.

## Возможности
- Ручные тест-кейсы из требований или OpenAPI (Allure TestOps as Code).
- Генерация UI/API автотестов по готовым ручным кейсам.
- Проверка стандартов (AAA, Allure-метки, naming/structure) и выгрузка отчёта.
- Оптимизация тестов (дубликаты, coverage, устаревшие) по репозиторию.
- Просмотр состояния интеграций (LLM, Compute API, GitLab) и health.

## Структура репо
- `backend/` — FastAPI-приложение (агенты, сервисы, хранилище, API v1).
- `frontend/` — React + Vite SPA (Dashboard, Jobs, Standards, Optimization).
- `docker-compose.yml` — запуск фронта, бэка и redis одной командой.

## Требования
- Docker + Docker Compose v2.
- Для локального запуска без контейнеров: Python 3.11, Node 20.

## Переменные окружения (backend)
Создайте `backend/.env` из `backend/.env.example` и заполните секреты:
- `LLM_API_KEY` — ключ Cloud.ru LLM (иначе LLM-фичи отключены).
- `LLM_BASE_URL` — endpoint LLM (по умолчанию `https://foundation-models.api.cloud.ru/v1`).
- `LLM_MODEL` — модель (например `openai/gpt-oss-120b`).
- `COMPUTE_API_URL`, `COMPUTE_API_TOKEN`, `COMPUTE_PROJECT_ID` — доступ к Evolution Compute (опционально).
- `GITLAB_URL`, `GITLAB_TOKEN`, `GITLAB_PROJECT_ID` — интеграция с GitLab (опционально).
- `ENVIRONMENT` — `development`/`production`.
- `STORAGE_PATH`, `TEMP_PATH` — каталоги для результатов/временных файлов (мапятся в volumes).

Frontend читает `VITE_API_BASE` (по умолчанию `http://localhost:8000/api`) для запросов к бэку.

## Запуск через Docker Compose (рекомендуется)
1. Скопируйте `backend/.env.example` → `backend/.env` и задайте значения.
2. Соберите и поднимите сервисы:
   ```bash
   docker compose up --build
   ```
3. Откройте UI: http://localhost:3000  
   API/Docs: http://localhost:8000/docs , health: http://localhost:8000/health

Порты: `3000` (frontend), `8000` (backend), `6379` (redis).  
Volumes: `backend_storage` → `/data/storage`, `backend_temp` → `/data/temp`, `redis_data` → `/data`.

## Локальный запуск без Docker
Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd frontend
npm ci
npm run dev  # UI на http://localhost:5173 (при необходимости выставьте VITE_API_BASE)
```

## Полезные команды
- Frontend: `npm run lint`, `npm run build`.
- Backend (при наличии тестов): `pytest`.

## Примечания
- Redis сейчас не критичен, но зарезервирован под фоновые джобы.
- Playwright есть в зависимостях backend для генерации UI-тестов; его браузеры в контейнер не ставятся автоматически (нужно отдельно, если потребуется реальный запуск Playwright внутри контейнера).
