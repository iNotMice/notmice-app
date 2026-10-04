# ТЗ: Регистрация лабораторий и доступ к данным (двухуровневая модель, consent-gated)

Версия 1.0 · 2026-10-03 · Автор: Клава (по решениям Андрея) · Исполнитель: Бакыт (CTO)
Репозиторий: `iNotMice/notmice-app` · Цель: заявка SPRIND «Recoding Medicine», дедлайн **16.10.2026 18:00 CET**

---

## 0. Контекст и принятые решения

Задача — дать лабораториям возможность работать с данными платформы через **фильтры/выборки**, и собирать для этого нужные атрибуты **опросом** участников. Модель обязана соответствовать GDPR ст.9 (данные о здоровье — спецкатегория) и принципам SPRIND (*data protection и data sovereignty*).

**Решения (утверждены Андреем 2026-10-03):**
1. Модель доступа — **двухуровневая** (не построчный доступ ко всем данным):
   - **Уровень 1:** всем верифицированным лабам — только агрегатные **k-анонимные** срезы по фильтрам.
   - **Уровень 2:** построчные **псевдонимные** данные — только по пользователям, которые **явно согласились** участвовать в конкретном исследовании лабы.
2. Работаем под **дедлайн SPRIND 16.10.2026**. Объём режем до application-ready MVP (см. §11).

**Почему не построчный доступ ко всем (зафиксировать для ревью):** противоречит решению №6 брифа, требует Art 9(2)(a) явного согласия на каждую цель обработки, и ослабляет заявку SPRIND (там выигрывает суверенитет данных пользователя, а не раздача спецкатегории третьим лицам).

---

## 1. Текущее состояние (на что опираемся)

### 1.1 Пайплайн загрузки/хранения (проверено по коду)
- Файл анализа (PDF/фото) — **только в RAM**, в конце `del payload`; на диск/в БД **не сохраняется**. Хранится лишь `SHA-256` (`provenance.document_sha256`).
- Маскирование PII — локально (Tesseract/pdfium) **до** вызова модели; при неуверенности — превью на подтверждение пользователю.
- В модель (Gemini по умолчанию / Claude) уходит только замаскированный контент.
- На `confirm` данные чистятся `reject_pii` и пишутся в Postgres: `users` (псевдонимно) → `lab_results` → `biomarkers` (+ `provenance`). `credentials.email` — отдельная таблица.

### 1.2 Готовый фундамент (переиспользуем)
- `app/domain/cohort.py`: `CohortQuery` + `publish_count()` (k-анонимность: <10 → скрыть, иначе округлить вниз до кратного 5). **Намеренно не подключён к API до DPIA** — подключаем теперь.
- `app/api/dataset.py` + `services/dataset.py` + `repositories/dataset.py`: публичный opt-in датасет, `reject_sensitive_output` на выходе.
- Argon2id, одноразовые токены (SHA-256-дайджест), сессии-куки, rate-limit (per-IP + per-identity) — переиспользуем для лаб-аккаунтов.

### 1.3 Находки, которые чиним по пути
- **Consent-gap:** `research_reuse` (optional consent) собирается, но **нигде не используется как гейт**. Публичный датасет пускает только по `share_settings.is_public`. В новой модели: агрегатный explorer гейтится по **`research_reuse`** (правовое основание на исследовательскую переработку), `is_public` остаётся отдельным флагом «показывать мой профиль публично».
- **Демографии нет** — добавляем опросом (§5).
- **Трансфер в Gemini (США)** спецкатегории (даже замаскированной) — нужен DPA + SCC; зафиксировать в DPIA (§9).

---

## 2. Целевая архитектура

```
                         ┌─────────────────────────── Participant side ───────────────────────────┐
  Survey (controlled)    │  participant_profiles  (sex, year_of_birth, country, conditions[], ...)  │
  Consents               │  consents: health_data(req), research_reuse(opt), aggregate_stats(opt)   │
  Lab panels             │  users → lab_results → biomarkers (+ provenance)                         │
  Study opt-in           │  study_consents (user ↔ study, per-study, withdrawable)                  │
                         └────────────────────────────────────────────────────────────────────────┘
                                             │ research_reuse consent          │ study_consents
                                             ▼ (lawful basis)                  ▼ (Art 9(2)(a))
   ┌──────────────── Lab side ───────────────────────────┐        ┌──────────────────────────────────┐
   │ organizations (verified)                            │ TIER 1 │ TIER 2                             │
   │ lab_users (email+pwd, Argon2, sessions)             │ Aggreg.│ Study recruitment                  │
   │ DUA acceptance                                      │ k-anon │ pseudonymous row-level,            │
   │ POST /lab/cohorts/query → counts+stats (k≥10)       │ counts │ per-study pseudonym, scope-limited │
   │ GET  /lab/cohorts/facets                            │ only   │ GET /lab/studies/{id}/participants │
   │ lab_query_audit (accountability)                    │        │                                    │
   └─────────────────────────────────────────────────────┘        └──────────────────────────────────┘
```

Ключевые инварианты:
- Лаба **никогда** не видит `email`, `seed_phrase_hash`, внутренний `users.id`, `document_sha256`.
- Уровень 1 отдаёт **только агрегаты**, каждое число через `publish_count` (скрытие <10).
- Уровень 2 отдаёт строки **только** по `study_consents` и только поля из `data_scope`, под **per-study псевдонимом** (не глобальный `public_id`).
- Все запросы лаб — в `lab_query_audit`.

---

## 3. Модель данных (новые таблицы)

Новая миграция `0006_lab_access.py`. Ниже ORM-классы (`app/repositories/models.py`) и перечисление enum (`app/domain/enums.py`). Все `Uuid` PK, TZ-aware `DateTime`.

### 3.1 Enums (`app/domain/enums.py`, добавить)
```python
class SexAtBirth(StrEnum):
    """Non-identifying sex field for cohort stratification."""
    FEMALE = "female"
    MALE = "male"
    INTERSEX = "intersex"
    UNDISCLOSED = "undisclosed"


class OrganizationType(StrEnum):
    """Kind of data consumer. All are verified before any access."""
    LAB = "lab"
    RESEARCH_INSTITUTE = "research_institute"
    UNIVERSITY = "university"
    COMPANY = "company"


class VerificationStatus(StrEnum):
    """Manual moderation state of an organization."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class StudyStatus(StrEnum):
    """Lifecycle of a recruitment study. Only OPEN is visible to participants."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    OPEN = "open"
    CLOSED = "closed"


class LabRole(StrEnum):
    """Role of a member inside an organization."""
    OWNER = "owner"
    MEMBER = "member"
```

### 3.2 Participant profile (опрос) + контролируемые справочники
```python
class ParticipantProfile(Base):
    """Non-identifying survey answers used only for cohort stratification.

    No free text, no direct identifiers. Age is a year, never a full date of
    birth. Every column is a quasi-identifier handled by k-anonymity on output.
    """
    __tablename__ = "participant_profiles"
    __table_args__ = (
        CheckConstraint(
            "year_of_birth IS NULL OR year_of_birth BETWEEN 1900 AND 2015",
            name="ck_profiles_year_of_birth",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    sex_at_birth: Mapped[str | None] = mapped_column(String(16), nullable=True)
    year_of_birth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)  # ISO-3166-1 alpha-2
    height_cm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    weight_kg: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)
    smoking: Mapped[str | None] = mapped_column(String(16), nullable=True)   # never/former/current
    alcohol: Mapped[str | None] = mapped_column(String(16), nullable=True)   # none/light/moderate/heavy
    activity: Mapped[str | None] = mapped_column(String(16), nullable=True)  # sedentary/light/moderate/high
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProfileCondition(Base):
    """One condition/goal code from a controlled vocabulary. Never free text."""
    __tablename__ = "profile_conditions"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_profile_conditions_user_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(48), nullable=False)  # e.g. "type2_diabetes"
```

Контролируемый словарь состояний/целей — в коде (`app/domain/survey.py`), не в БД свободным текстом: `CONDITION_CODES: frozenset[str]`, `GOAL_CODES`, плюс `SMOKING`, `ALCOHOL`, `ACTIVITY` допустимые значения. Валидатор отклоняет всё вне словаря.

### 3.3 Организации и лаб-пользователи (отдельный контур аутентификации)
```python
class Organization(Base):
    """A data consumer. No access to any data until verified and DUA-signed."""
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_type: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    dua_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dua_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LabUser(Base):
    """Login material for an organization member. Fully separate from participants."""
    __tablename__ = "lab_users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)
    email_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```
`lab_sessions` и `lab_auth_tokens` — структурно копируют `login_sessions` / `auth_tokens`, но ссылаются на `lab_users.id` и используют отдельное имя cookie `notmice_lab_session`. Переиспользовать `new_auth_token`, `auth_token_digest`, `Argon2PasswordHasher`.

### 3.4 Исследования и согласие на участие (Уровень 2)
```python
class Study(Base):
    """A recruitment request by a verified organization. Moderated before OPEN."""
    __tablename__ = "studies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(String(2000), nullable=False)  # reviewed, PII-checked
    cohort_query: Mapped[dict] = mapped_column(JSONB, nullable=False)   # snapshot of CohortQuery
    data_scope: Mapped[dict] = mapped_column(JSONB, nullable=False)     # which fields/markers shared
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudyConsent(Base):
    """Explicit per-study opt-in. Withdrawable. This is the Art 9(2)(a) record."""
    __tablename__ = "study_consents"
    __table_args__ = (
        UniqueConstraint("user_id", "study_id", name="uq_study_consents_user_study"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    study_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("studies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    data_scope: Mapped[dict] = mapped_column(JSONB, nullable=False)  # frozen at opt-in time
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LabQueryAudit(Base):
    """Every lab query, for GDPR accountability (Art 5(2)) and differencing review."""
    __tablename__ = "lab_query_audit"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lab_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("lab_users.id"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("organizations.id"), index=True)
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False)
    query: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_cohort_size: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # published (k-anon)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```
Импорты: `from sqlalchemy import SmallInteger`; `from sqlalchemy.dialects.postgresql import JSONB`.

---

## 4. Каталог согласий (`app/domain/consents.py`, диф)

```python
HEALTH_DATA = "health_data"               # required (как сейчас)
RESEARCH_REUSE = "research_reuse"          # optional: включить мои псевдонимные записи в
                                           # исследовательский датасет И агрегатную статистику лаб
HEALTH_DATA_VERSION = "2026-10-03"         # ← поднять версию, тексты обновлены юристом
RESEARCH_REUSE_VERSION = "2026-10-03"
```
- Агрегатный explorer (Уровень 1) включает участника **только** при активном `research_reuse` (не `is_public`).
- Participant-профиль (опрос) допускается без `research_reuse`, но в выборки лаб такой участник **не попадает**, пока согласие не дано.
- Per-study согласие (Уровень 2) — **не** статический каталог, а запись `study_consents` (дано в кабинете на конкретное исследование).
- При смене версии текста `research_reuse` — участник, у кого старая версия, выпадает из агрегаций до повторного согласия (как уже устроено `ConsentVersionError`).

⚠️ Тексты всех согласий и DUA — **утверждает юрист до прод-деплоя** (блокер запуска, но не блокер подачи заявки).

---

## 5. Опрос участника (survey) — API

- `GET /api/v1/accounts/me/profile` → текущий профиль (владелец).
- `PUT /api/v1/accounts/me/profile` → upsert профиля; тело — только контролируемые значения; `reject_pii` обязателен; свободного текста нет.
- `GET /api/v1/survey/catalog` → публичный справочник допустимых кодов (для UI): страны, состояния, цели, уровни курения/алкоголя/активности, версии текстов согласий.

Pydantic (пример, стиль репо — `extra="forbid"`, валидация словарём):
```python
class ProfileUpdateRequest(BaseModel):
    """Survey answers. Controlled vocabulary only; no free text, no DOB."""
    model_config = ConfigDict(extra="forbid")

    sex_at_birth: Literal["female", "male", "intersex", "undisclosed"] | None = None
    year_of_birth: int | None = Field(default=None, ge=1900, le=2015)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    height_cm: int | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=30, le=400)
    smoking: Literal["never", "former", "current"] | None = None
    alcohol: Literal["none", "light", "moderate", "heavy"] | None = None
    activity: Literal["sedentary", "light", "moderate", "high"] | None = None
    conditions: list[str] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def _check_condition_codes(self) -> "ProfileUpdateRequest":
        from app.domain.survey import CONDITION_CODES
        unknown = set(self.conditions) - CONDITION_CODES
        if unknown:
            raise ValueError("unknown condition code")
        return self
```
Где собирать: отдельный шаг онбординга **после** подтверждения email (не «перед регистрацией» в смысле до аккаунта — иначе пришлось бы хранить данные здоровья без аккаунта/согласия; «перед доступом лаб» = участник заполняет профиль в кабинете). Это важно для GDPR: сбор только после `health_data`-согласия.

---

## 6. Уровень 1 — Агрегатный explorer когорт

### 6.1 Контракт запроса (расширяем `CohortQuery`)
```python
class CohortFilter(BaseModel):
    """Closed cohort filter. Any unknown field is rejected."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    sex_at_birth: tuple[Literal["female", "male", "intersex", "undisclosed"], ...] = ()
    age_bands: tuple[Literal["18-29", "30-39", "40-49", "50-59", "60-69", "70-plus"], ...] = ()
    countries: tuple[str, ...] = Field(default=(), max_length=20)
    conditions: tuple[str, ...] = Field(default=(), max_length=10)
    markers: tuple[str, ...] = Field(default=(), max_length=5)        # LOINC или canonical
    collected_from: date | None = None
    collected_to: date | None = None
```

Период анализа задаётся включительными датами сбора образца; без обеих дат учитывается вся доступная история. Для маркера берётся только последнее подтверждённое измерение каждого участника внутри периода. Фильтр по дневнику протоколов/вмешательств исключён: записи дневника остаются приватными данными участника.

### 6.2 Эндпоинты (auth: верифицированная лаба + DUA)
| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/v1/lab/cohorts/query` | Размер когорты (k-anon) + агрегаты по запрошенным маркерам |
| GET | `/api/v1/lab/cohorts/facets` | Доступные значения фильтров со счётчиками (k-anon) |

Ответ `query` (каждое число — через `publish_count`, иначе `null`):
```json
{
  "cohort_size": 45,
  "markers": [
    {"loinc_code":"2093-3","canonical_name":"Cholesterol","n":40,"unit":"mg/dL",
     "mean":198.3,"median":195.0,"p25":171.0,"p75":223.0}
  ],
  "suppressed": false
}
```

### 6.3 Правила k-анонимности и защита (ОБЯЗАТЕЛЬНЫ)
- Популяция = участники с активным `research_reuse` и подтверждёнными `lab_results`.
- `cohort_size` и `n` каждого маркера → через `publish_count` (скрытие <10, округление до 5). Если `cohort_size` скрыт → весь ответ `suppressed=true`, статистик нет.
- Статистики (mean/median/перцентили) считать только при `n ≥ 10`; значения округлять (например до 1 знака) — анти-реконструкция.
- В выдаче `facets` показывать только значения со счётчиком не меньше 10; значения ниже порога не возвращаются.
- На маркер и единицу измерения статистика считается отдельно. Внутри участника повторные измерения не считаются независимыми наблюдениями.
- **Анти-differencing:** каждый запрос пишется в `lab_query_audit`; действует лимит 200 запросов на организацию за UTC-день. Серия из пяти похожих запросов по малым когортам за 15 минут вызывает внутреннее предупреждение без записи значений фильтров в лог. Полноценный differential privacy — в бэклог (§11, фаза C).
- Выход прогонять через аналог `reject_sensitive_output` (убедиться, что ни один внутренний id/`public_id` не просочился — на Уровне 1 `public_id` не возвращается вообще).

### 6.4 SQL-слой
Новый `repositories/cohort.py`: джоины `users → participant_profiles / profile_conditions / lab_results → biomarkers`, фильтр по `consents` (`research_reuse`, не withdrawn, текущая версия). Агрегаты через `func.count`, `func.avg`, `func.percentile_cont`. Параметризация строго через SQLAlchemy (без строковой конкатенации).

---

## 7. Уровень 2 — Рекрутинг в исследования (consent-gated, построчно)

### 7.1 Поток
1. Лаба создаёт `Study` (draft) с `cohort_query` и `data_scope` (какие маркеры/поля нужны).
2. NotMice-админ модерирует (`in_review` → `open`); `purpose` проверяется на PII и на отсутствие мед-обещаний.
3. Подходящие участники (`research_reuse` + матч по профилю) видят приглашение в кабинете: «Исследование X, лаба Y, будут переданы: <data_scope>». Текст — что именно уходит.
4. Участник **явно соглашается** → `study_consents` (фиксируется `data_scope` на момент согласия).
5. Лаба получает построчные **псевдонимные** данные **только согласившихся**, только поля `data_scope`, под **per-study псевдонимом**.
6. Участник может **отозвать** согласие в кабинете → строка исключается из будущих выдач, лаба уведомляется; ранее выгруженное регулируется DUA.

### 7.2 Per-study псевдоним (анти-линкидж между исследованиями)
Не отдавать глобальный `public_id`. Для каждого исследования — свой идентификатор (PQC-стандарт проекта: **HMAC-SHA-512**, не SHA-256):
```python
import hashlib, hmac

def study_pseudonym(study_id: uuid.UUID, user_id: uuid.UUID, pepper: bytes) -> str:
    """Stable per-study id so a lab cannot link a participant across studies.

    pepper = settings.study_pseudonym_secret (>=32 bytes, env, never in VCS).
    """
    msg = f"{study_id}:{user_id}".encode("utf-8")
    return hmac.new(pepper, msg, hashlib.sha512).hexdigest()[:32]
```
Добавить `STUDY_PSEUDONYM_SECRET` в `config.py` + `validate_runtime_secrets` (как `seed_hash_secret`).

### 7.3 Эндпоинты
| Метод | Путь | Кто | Назначение |
|---|---|---|---|
| POST | `/api/v1/lab/studies` | лаба | создать study (draft) |
| GET | `/api/v1/lab/studies/{id}/participants` | лаба | построчные данные согласившихся (per-study pseudonym, scope-limited) |
| GET | `/api/v1/accounts/me/study-invitations` | участник | приглашения по матчу |
| POST | `/api/v1/accounts/me/study-consents` | участник | согласиться на участие |
| DELETE | `/api/v1/accounts/me/study-consents/{study_id}` | участник | отозвать |

---

## 8. Лаб-аккаунты: регистрация, верификация, DUA

> **Важно (проверено по коду 2026-10-03):** в текущем репо `notmice-app` **нет** никакого админ-контура, ролей и модерации — только участники + публичный датасет. Верификация лаб строится с нуля. Поэтому ниже механизм расписан явно.

### 8.1 Регистрация
- `POST /api/v1/lab/register` (организация + первый owner: email+пароль ≥12). Письмо-подтверждение — через уже работающий mailer (Resend).
- После подтверждения email организация в статусе `pending`. **Доступа к данным нет.**

### 8.2 Что значит «платформа понимает, что лаба верифицирована» — два слоя
**(1) Состояние (источник правды в БД):** `organizations.verification_status ∈ {pending, verified, rejected}` + `dua_version` / `dua_accepted_at`. Это записанное решение, не проверка сама по себе.

**(2) Гейт на каждом запросе (рантайм):** зависимость `require_verified_lab` на всех `/lab/*`, по аналогии с нынешним `get_current_user` участника. `verified` — необходимое, но недостаточное: нужны ещё подтверждённый email и принятый DUA актуальной версии.
```python
async def require_verified_lab(
    request: Request,
    lab_service: Annotated[LabService, Depends(get_lab_service)],
) -> VerifiedLabPrincipal:
    """Resolve the lab session cookie and assert the org may read data.

    Raises:
        HTTPException(401): session missing/expired or email not confirmed.
        HTTPException(403): organization not verified or DUA not current.
    """
    lab_user = await lab_service.authenticate(request.cookies.get(LAB_SESSION_COOKIE_NAME))
    if lab_user.email_confirmed_at is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email not confirmed")
    org = await lab_service.get_organization(lab_user.organization_id)
    if org.verification_status != VerificationStatus.VERIFIED.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organization not verified")
    if org.dua_version != CURRENT_DUA_VERSION:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Data Use Agreement not accepted")
    return VerifiedLabPrincipal(lab_user_id=lab_user.id, organization_id=org.id, role=lab_user.role)
```
DUA принимается самой лабой: `POST /api/v1/lab/dua/accept` (фиксирует `dua_version`, `dua_accepted_at`).

### 8.3 Кто и как ставит `verified` (ручная проверка)
Флаг выставляет **человек** (оператор NotMice) после внекодовой проверки, что лаба реальна:
- юрлицо по реестру (рег. номер страны);
- домен: email владельца = корпоративный домен организации (не публичная почта);
- принятый DUA.
Проверка фиксируется (кто/когда/доказательство) — минимально в `organizations` + лог.

**Механизм выставления флага (MVP под дедлайн):** админ-UI не строим. Флаг ставится **CLI-скриптом** в духе существующих `scripts/seed_*.py`:
```
python -m app.scripts.verify_organization --org <uuid> --status verified --operator <id> --evidence "VAT DE…, domain match"
```
**Эволюция (после подачи):** внутренний эндпоинт `POST /internal/organizations/{id}/verify` под `X-Internal-Token` (паттерн из PQC-проекта), затем — админ-роль и UI.

### 8.4 Прочее
- Rate-limit per-lab (отдельный бакет). Сессии — отдельная кука `notmice_lab_session`, отдельные таблицы. Контуры participant/lab **не пересекаются** (сохраняем изоляцию identity/health).
- `revoke`: установка `verification_status='rejected'` немедленно закрывает доступ (гейт на каждом запросе это увидит).

---

## 9. GDPR / DPIA / безопасность (обязательная часть для SPRIND)

- **Правовое основание:** Art 6(1)(a) + **Art 9(2)(a) явное согласие**. Уровень 1 — `research_reuse`; Уровень 2 — `study_consents` на каждую цель.
- **Минимизация:** опрос — контролируемый словарь, без свободного текста; `year_of_birth`, не дата рождения; per-study псевдоним; `data_scope` ограничивает поля.
- **k-анонимность** (≥10) + супрессия + округление; differencing — аудит + бюджет запросов (DP в бэклог).
- **DPIA** — обязательна до прод-запуска фичи (решение №7 брифа). Эта фича — триггер DPIA. Подать можно с «DPIA in progress».
- **Записи обработки (Art 30)**, **DUA** с лабами (контролёр-контролёр; при необходимости — анализ совместного контролёрства), **международные трансферы** (Gemini США — DPA+SCC; рассмотреть ЕС-регион/он-прем модель извлечения для заявки).
- **Изоляция в БД:** усилить логическое разделение identity/health — Postgres **RLS** и/или отдельная схема для `credentials`/`lab_users`; приложение под ролью без `BYPASSRLS`. (Связано с практикой из PQC-проекта.)
- **Удаление (Art 17):** каскады уже стоят (`ondelete=CASCADE`); проверить, что удаление участника вычищает профиль/согласия/участия; отзыв study-согласия исключает из будущих выдач.
- **Право на доступ/портируемость:** экспорт участника расширить профилем и списком согласий/участий.

---

## 10. Привязка к критериям SPRIND

| Требование SPRIND | Чем закрываем |
|---|---|
| Доступ к ≥1 уникальному датасету здоровья | Opt-in псевдонимный датасет биомаркеров + демография из опроса (CC0-агрегаты, CC BY-схемы) |
| ≥1 конкретное AI-приложение | Vision-экстракция анализов (`vision.py`) + биологический возраст/PhenoAge (`phenoage.py`); для заявки оформить как AI-пайплайн «фото анализа → структурированные маркеры → биовозраст/когортная аналитика» |
| Ответственное обращение с данными, data sovereignty | Двухуровневая consent-gated модель, per-study согласие+отзыв, k-анонимность, маскирование до модели, файлы не хранятся |
| Публичный вклад | Открытые CC0-агрегаты, CC BY-схемы/словари, AGPL-код |

---

## 11. План по фазам (к 16.10 и после)

**Фаза A — Данные/опрос (цель ~09.10).** Миграция `0006` (participant_profiles, profile_conditions), `survey.py` словари, профиль-API (§5), подъём версий согласий, гейт агрегаций по `research_reuse`. Итог: датасет обогащён демографией → «уникальный, курируемый».

**Фаза B — Агрегатный explorer + лаб-аккаунты (цель ~13.10).** Таблицы organizations/lab_users/sessions, `/lab/register` + верификация, `require_verified_lab`, `/lab/cohorts/query|facets` на `cohort.py` + `repositories/cohort.py`, `lab_query_audit`. Итог: демонстрируемый data-sovereign доступ лаб.

**Фаза C — после подачи.** Уровень 2 (studies, study_consents, per-study pseudonym, приглашения/отзыв), DP-хардненинг бюджета запросов, портал-UI, RLS, перенос извлечения в ЕС-регион.

**Параллельно (не код):** DPIA (draft), тексты согласий+DUA у юриста, описание датасета и governance для заявки.

> Риск сроков: Фаза A+B за ~10 дней реальна для одного разработчика только при урезанном UI (API + минимальные экраны). Если не успеваем B — для заявки достаточно A (обогащённый датасет) + описание архитектуры B/C как плана. Приоритет при нехватке времени: A > B-API > B-UI.

### Статус реализации фазы A

- Добавлены миграция `0006`, контролируемая схема профиля, owner-scoped API, полный каталог ISO-3166-1 alpha-2, версии текущих согласий и включение профиля в личные JSON/CSV-выгрузки. В кабинете показывается состояние опроса; полноценная форма не включена.
- Сбор закрыт по умолчанию: `SURVEY_ENABLED=false`, `PARTICIPANT_PROFILE_VERSION` не задан. При этих настройках `GET`/`PUT` профиля отвечают `503`; `DELETE` своего профиля остаётся доступен для удаления данных. Включение без утверждённой версии согласия блокирует запуск приложения. Опрос не собирает ответы.
- Проверены профильные API/гейты/экспорт, типы и сборка. Alembic-схема сгенерирована в offline SQL; проверка `alembic check` требует доступной PostgreSQL, которой в текущей среде нет.
- Фаза A не считается готовой к сбору или передаче исследователям: остаются правовое утверждение цели и текста согласия, научное утверждение словаря состояний и целей, подключение гейта `research_reuse` к будущей агрегатной выдаче и проверка миграции на PostgreSQL.

### Статус фазы B (API-инкремент)

- Добавлены миграции `0007`–`0009` и отдельные таблицы `organizations`, `lab_users`, `lab_sessions`, `lab_auth_tokens`, `lab_query_audit`. Таблицы учётных записей лабораторий не ссылаются на участников; DUA и состояние ручной верификации хранятся у организации.
- Реализованы lab-регистрация организации и владельца, подтверждение email, отдельная серверная сессия `notmice_lab_session`, вход/выход, просмотр собственного статуса, ручная CLI-верификация с фиксацией оператора, времени и основания, а также явное принятие DUA только после верификации.
- Добавлен пользовательский интерфейс `/lab`: регистрация владельца и организации, вход, возврат из email-подтверждения, просмотр статуса верификации/DUA и доступное действие принятия только после утверждения текущей версии DUA. Ссылка на портал есть в основной навигации; интерфейс локализован на английский и немецкий.
- Ссылка подтверждения сначала открывает отдельную страницу с кнопкой; сам GET не расходует токен, чтобы предварительное открытие письма почтовым сканером не подтверждало адрес.
- Добавлен SQL-предикат внутреннего агрегатного репозитория: участник считается подходящим только при активном `research_reuse` текущей версии и наличии подтверждённого анализа. Возвращается только подавленный/округлённый размер, не сырая численность. Публичная выдача и `is_public` не используются как замена исследовательскому согласию.
- Подключены `POST /api/v1/lab/cohorts/query` и `GET /api/v1/lab/cohorts/facets` за проверкой подтверждённого email, ручной верификации организации и действующего DUA. Cohort query применяет только текущий активный `research_reuse`, выдаёт подавленные/округлённые агрегаты и считает не более одного последнего результата на участника/маркер/период. Узкие значения facets скрыты; запросы аудируются, ограничены 200 на организацию в UTC-день, а серия похожих запросов по малым когортам вызывает внутреннее предупреждение.
- В кабинете лаборатории добавлен cohort explorer: фильтры по LOINC-маркерам (до 5), полу, возрасту, странам (до 20), состояниям (до 10) и включительному диапазону дат; отображаются только разрешённые API агрегаты, с понятными состояниями подавления и ошибок. Интерфейс вызывает endpoints только при подтверждённом допуске организации и принятой актуальной DUA; тексты переведены на английский и немецкий. Фильтры и результаты не содержат participant-level данных или внутренних идентификаторов.
- `CURRENT_DUA_VERSION` пока не задан, поэтому DUA нельзя принять и обе выдачи остаются закрытыми. Построчного API лабораторий нет.
- Проверка PostgreSQL миграций остаётся блокированной: Docker daemon и локальный сервер PostgreSQL в среде недоступны; offline SQL можно проверить отдельно.

---

## 12. Тесты и критерии приёмки

- Юнит: `publish_count` на границах (9/10/14/15); агрегатор не отдаёт статистику при `n<10`; `study_pseudonym` стабилен и различается по study; валидатор опроса режет коды вне словаря и любой PII (`reject_pii`).
- Контрактные: `/lab/cohorts/query` без DUA/verified → 403; participant без `research_reuse` не попадает в агрегаты; `/lab/studies/{id}/participants` не отдаёт не-согласившихся и не содержит `email`/`public_id`/внутренних id (прогон через output-guard).
- Безопасность: попытка differencing (серия узких фильтров) — покрытие аудитом; отзыв study-согласия исключает строку из следующей выдачи.
- Golden: агрегатный ответ на фикстурной когорте из 12 участников = корректные округлённые числа.
- CI: `ruff`, `mypy strict`, `pytest`, `alembic check` — зелёные (как в текущем проекте).

## 13. Открытые вопросы (к Андрею/юристу/DPIA)
1. Тексты согласий `research_reuse` (v2026-10-03) и DUA — кто и к какой дате утверждает.
2. Контролёр vs совместный контролёр с лабами — юридическая квалификация (влияет на DUA).
3. Трансфер в Gemini: оставляем с DPA+SCC или для заявки заявляем переход на ЕС-регион/он-прем извлечение.
4. Нужен ли европейский партнёр-лаборатория для заявки (в условиях SPRIND явного требования консорциума нет, но «matchmaking» и демонстрируемый партнёр усиливают) — контакт французской лабы от Кристины.
5. Набор кодов состояний/целей для опроса (стартовый словарь) — согласовать с научным контактом (Пешкин — методология).

---
🤖 Подготовлено Claude Code для передачи CTO. Код в ТЗ — реализуемые образцы в стиле репозитория (Pydantic v2, SQLAlchemy 2.0, async, type hints).
