# TestOps Copilot Frontend (React + TS + Vite)

## Запуск
```bash
cd frontend
npm install
npm run dev
```
Переменные окружения:
- `VITE_API_BASE` — базовый URL бэкенда (например `http://localhost:8000/api/v1`).

## Скрипты
- `npm run dev` — локальная разработка.
- `npm run build` — production сборка.
- `npm run preview` — предпросмотр.
- `npm run lint` — ESLint.
- `npm run test` — Vitest (smoke).

## Структура
- `src/pages` — экраны (Dashboard, Testcases, Autotests, Standards, Optimization, Settings, Jobs).
- `src/services/api` — клиенты к `/api/v1` (testcases, autotests, standards, optimization, integrations, config).
- `src/types/api.ts` — DTO и zod-схемы, синхронные с `backend/src/models/dto.py`.
- `src/hooks` — `usePolling`, `useJobWatcher`.
- `src/styles` — тема/глобальные стили.

## Docker
```bash
cd frontend
docker build -t testops-frontend .
docker run -p 4173:4173 testops-frontend
```

