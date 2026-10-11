# NotMice

**An open, privacy-first platform for biological-age and biomarker research.**

[![License: AGPL-3.0](https://img.shields.io/badge/code-AGPL--3.0-blue.svg)](LICENSE)
[![backend](https://github.com/iNotMice/notmice-app/actions/workflows/backend.yml/badge.svg)](https://github.com/iNotMice/notmice-app/actions/workflows/backend.yml)
[![frontend](https://github.com/iNotMice/notmice-app/actions/workflows/frontend.yml/badge.svg)](https://github.com/iNotMice/notmice-app/actions/workflows/frontend.yml)

NotMice turns a routine blood panel into a longitudinal, pseudonymous record of biological-age
markers. A participant uploads a lab report, confirms the values the system reads from it, and
follows how those markers change over time. Researchers and laboratories work with a
consent-based, aggregated dataset — never with raw, identifiable records.

The name is a statement of method. Most longevity findings come from mice, worms and cell
cultures; NotMice makes clear, for every data point, that the subject is a human being.

> **Not a medical device.** NotMice computes the PhenoAge *research index* (Levine et al.,
> *Aging* 2018). It is a self-observation and research tool — not a diagnosis, a treatment
> recommendation, or a substitute for a physician.

---

## Why it exists

1. **A unique, curated health dataset.** Standardised blood-panel markers, contributed with
   explicit consent, pseudonymised, and published as open aggregates.
2. **A concrete AI application on top of it.** A vision pipeline reads markers from a PDF, scan
   or photo of a lab report; the PhenoAge index is computed server-side from the confirmed
   values.
3. **Data sovereignty by design.** The individual owns their data: granular consent, per-study
   opt-in, withdrawal at any time, and open aggregates for science — with no sale of raw data.

## The PhenoAge research index

PhenoAge (Levine ME et al., *Aging (Albany NY)*. 2018;10(4):573–591) estimates a biological age
from nine standard blood markers plus chronological age. **All nine are required** for a score:

`Albumin · Creatinine · Glucose · C-reactive protein · Lymphocyte % · Mean corpuscular volume (MCV) · Red-cell distribution width (RDW) · Alkaline phosphatase (ALP) · White-blood-cell count (WBC)`

The index is presented strictly as a research signal, with the lab's own reference interval and
a fixed disclaimer. No risk language, no "years saved", no supplement, dose or diet advice.

## Data governance & privacy (GDPR Art. 9)

Health data is a special category under GDPR. The platform is built around that from the ground up:

- **No direct identifiers stored.** No name, date of birth or patient number. A participant is a
  pseudonymous `public_id`; email credentials live in a separate table that the analytics path
  never joins.
- **Original files are never stored.** An upload is held in memory only; just its SHA-256 is kept
  for provenance.
- **PII removed before any model call.** Lab reports are redacted locally (headers masked) before
  a single byte reaches the extraction model; uncertain frames require human confirmation. Inputs
  and public outputs both pass a PII guard.
- **k-anonymity for aggregates.** Cohort counts below 10 are suppressed and the rest are rounded
  down to a multiple of 5.
- **Explicit, versioned consent.** Separate grants for providing the service, for research reuse,
  and for public sharing — each withdrawable.
- **Open by consent, deletable by right.** Aggregates are published; individual pseudonymous
  records are removable on request (GDPR Art. 17).

A Data Protection Impact Assessment (DPIA) and the physical separation of identity / health /
research stores (with database-level Row-Level Security) are prerequisites to the public launch;
live laboratory access stays gated behind the DPIA.

## Laboratory access — two tiers, consent-gated

Laboratories never browse raw participant data. Access is designed in two tiers:

- **Tier 1 — Aggregate cohort explorer.** Verified labs query cohorts by non-identifying filters
  (sex, age bands from 18+, country, condition codes, markers) and receive only k-anonymised
  counts and distributions.
- **Tier 2 — Study recruitment.** A lab publishes a study; matching participants who have given
  explicit consent opt in per study. Only then does the lab receive **pseudonymous, scope-limited
  row-level data** for those participants, under a per-study pseudonym (no cross-study linkage),
  revocable at any time.

Every verified-lab query is audited. Activation is gated behind the DPIA and signed data-use
agreements.

## Architecture

```
Browser (React/Vite SPA)
      │  HTTPS, TLS 1.3
      ▼
nginx reverse proxy ───────────────┐  serves the built SPA, terminates TLS,
      │  /api                      │  adds HSTS/CSP/security headers
      ▼                            ▼
FastAPI (async) ──────────► PostgreSQL + pgvector
      │                     users · lab_results · biomarkers · provenance ·
      │                     consents · participant_profiles · organizations …
      ▼
Google Gemini  (redacted lab images → structured markers; news translation)
```

One VPS runs the whole production stack (`postgres` + `api` + `proxy`) via Docker Compose.
Database migrations are applied automatically on API start-up.

## Security

- **TLS 1.3 only**, HSTS, a strict Content-Security-Policy, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`.
- **Argon2id** password hashing; recovery-phrase accounts stored only as Argon2id hashes.
- **One-time tokens** for e-mail confirmation and password reset (only the SHA-256 digest is stored); server sessions as `HttpOnly` + `Secure` + `SameSite` cookies.
- **Rate limiting** per IP and per identity; uniform responses that do not reveal whether an account exists.
- **Secrets via environment only** — none in the repository; production refuses to boot with dev-default secrets or with outbound mail unconfigured.
- **Infrastructure hardening**: key-only SSH with `fail2ban`, database and admin interfaces not exposed to the public internet.

## Open data & licensing

| Artifact | License |
|---|---|
| Source code | **AGPL-3.0-or-later** |
| Schemas, dictionaries & controlled vocabularies | **CC BY 4.0** |
| Aggregated public biomarker dataset (CSV / Parquet) + its Datasheet | **CC0-1.0** |

The public dataset ships with a *Datasheets for Datasets*-style description and is downloadable
as CSV, Parquet and a human-readable datasheet.

## Tech stack

FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2 · PostgreSQL + pgvector · Alembic ·
React + Vite + Tailwind CSS · nginx · Docker Compose · Google Gemini (vision + translation) ·
`tenacity`, `structlog`, `pytesseract`/`pdfium` (local redaction).

## Repository layout

```
app/            FastAPI backend
  api/          HTTP routers (accounts, cabinet, uploads, dataset, exports,
                survey, protocol, phenoage, lab_accounts, lab_cohorts, news, health)
  services/     use-cases (no HTTP / no ORM)
  domain/       pure domain logic, schemas, PII guards, consent catalogue
  repositories/ SQLAlchemy models and data access
  migrations/   Alembic migrations
  tests/        unit, contract and golden tests
src/            React/Vite single-page application
proxy/, web/    nginx configuration and the proxy image
docker-compose*.yml   local, production and TLS compose files
```

## Running locally

Requirements: Docker and Docker Compose.

```bash
# Backend + database + proxy (dev defaults are safe for local use only)
docker compose up --build
```

Frontend development server (hot reload):

```bash
npm install
npm run dev
```

Backend configuration is read from the environment (`app/core/config.py`); non-production
environments accept documented dev defaults. Copy and adjust before running against real data.

## Production

A single VPS serves everything over HTTPS:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.tls.yml up -d --build
```

All required secrets (database password, `SEED_HASH_SECRET`, `JWT_SECRET`, `PUBLIC_APP_URL`,
`SMTP_HOST`, CORS origins, docs auth) are provided from the host environment; the stack refuses
to start if any is missing. Live site: **https://notmice.com**.

## Quality

Continuous integration runs on every push and pull request:

- **Backend** — `ruff` lint, `ruff format --check`, `mypy --strict`, `alembic upgrade head`, and
  the full `pytest` suite (271 tests: unit, contract, golden, and Postgres integration).
- **Frontend** — TypeScript type-check (`tsc --noEmit`) and a production build.

## Roadmap

- Post-quantum TLS (hybrid X25519 + ML-KEM-768) once the proxy's TLS stack supports it.
- Migration of auth/pseudonym digests from SHA-256 to SHA-512.
- Physical separation of identity / health / research stores with Row-Level Security.
- DPIA sign-off and activation of Tier-2 study recruitment.

## License

Source code is licensed under the **GNU Affero General Public License v3.0 or later** — see
[`LICENSE`](LICENSE). Data and schema licensing is described under *Open data & licensing* above.

---

*NotMice is a research and self-observation platform. It does not provide medical advice,
diagnosis or treatment.*
