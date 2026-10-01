# Техническая Архитектура и Инженерный Регламент

> **Архив.** Рабочий документ — [TZ_v2.1_AGREED.md](TZ_v2.1_AGREED.md). Этот текст оставлен как история и не задаёт текущую работу.

## 1. Технологический стек (Tech Stack)
- **Backend:** Python 3.12+, FastAPI (async)[cite: 1, 6].
- **ORM & Database:** SQLAlchemy 2.0 (asyncio), PostgreSQL 16+, Alembic[cite: 1].
- **Pydantic:** Pydantic v2 (строгая валидация схем и PII-фильтрация)[cite: 1].
- **OCR / LLM Integration:** `pdfplumber` (для текстовых PDF), Anthropic Claude API (`claude-3-5-sonnet`) с поддержкой `prompt caching` и `tenacity` retry-логики[cite: 1].
- **Frontend / CMS:** Astro (SSR/SSG), TailwindCSS, Minimal TypeScript (Islands architecture)[cite: 1].
- **DevOps / CI:** Docker, Docker Compose, GitHub Actions, structlog[cite: 1, 6].

## 2. Структура проекта (Clean Architecture)
```text
app/
├── core/          # config.py (pydantic-settings), logging.py, deps.py
├── domain/        # Pydantic v2 модели, схемы, Enum, PII-валидаторы
├── repositories/  # Доступ к БД, SQLAlchemy async, без бизнес-логики
├── services/      # Бизнес-логика: парсинг, LOINC, PhenoAge, экспорт
├── api/           # FastAPI роутеры (только валидация входа и вызов сервисов)
├── migrations/    # Alembic скрипты
└── tests/         # Pytest юнит и интеграционные тесты

Правило: Роутер не знает про БД; Репозиторий не знает про HTTP; Сервис не знает ни про то, ни про другое[cite: 1].

3. Пайплайн обработки документов (Memory-Only Pipeline)
POST /api/v1/uploads/extract принимает UploadFile (PDF/Image).

Вычисление SHA-256 хеша в оперативной памяти.

Извлечение текста:

Текстовый PDF -> pdfplumber.

Изображение/Скан -> Claude Vision API с Pydantic Structured Output (RawLabExtraction).

Возврат клиенту JSON-структуры с извлеченными маркерами для визуальной проверки.

POST /api/v1/uploads/confirm принимает подтвержденный массив показателей, записывает в Postgres с привязкой к provenance.

Временный буфер файла очищается очисткой памяти (Garbage Collector).

4. Требования к качеству кода (Definition of Done)
Code Style: ruff (zero warnings), mypy --strict (без ошибок типов)[cite: 1].

Документирование: Google-style docstrings для каждой функции[cite: 1].

Безопасность: Конфигурация строго через .env + pydantic-settings. Zero credentials in repo[cite: 1].