# MyAIStats

**All your AI usage. One dashboard.**

[![CI](https://github.com/YOUR_USERNAME/my-ai-stats/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/my-ai-stats/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-v0.1.0-blue.svg)](https://github.com/YOUR_USERNAME/my-ai-stats/releases/tag/v0.1.0)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Local-first](https://img.shields.io/badge/privacy-local--first-purple.svg)](docs/SECURITY.md)

MyAIStats is an open-source, local-first application for tracking AI API usage, tokens, costs, credits, balances, and model pricing from one private dashboard. It runs on your machine, requires no registration, and keeps credentials and historical data local.

> **v0.1.0** — initial release. Demo Mode is enabled by default so the dashboard is useful before connecting an account.

## Why MyAIStats?

- **Local-first privacy** — backend binds to `127.0.0.1`; credentials are encrypted at rest with Fernet and never returned to the frontend.
- **Financial accuracy** — actual billed costs and estimated costs remain separate, with explicit labels and no double counting.
- **Confirmed balances only** — unsupported provider balance APIs are clearly marked instead of being guessed.
- **Multi-account support** — connect multiple accounts from the same provider.
- **Analytics** — daily/monthly spending, provider/model comparisons, token consumption, balance history, and audit history.
- **Export and ownership** — CSV/JSON exports plus SQLite backup and restore.
- **Demo Mode** — realistic records labeled `[DEMO]` make the interface immediately explorable.

## Supported Connectors

Capabilities are based on official documented APIs only. See [`docs/PROVIDER_CAPABILITIES.md`](docs/PROVIDER_CAPABILITIES.md) for authentication details, permissions, and endpoint notes.

| Provider | Priority | Connection | Usage | Costs | Balance | Pricing |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| OpenAI | P1 | ✅ | ✅ Admin key | ✅ Admin key | — | ✅ |
| OpenRouter | P1 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Anthropic | P2 | ✅ | ✅ Admin key | ✅ Admin key | — | ✅ |
| Google Gemini | P2 | ✅ | — | — | — | ✅ |
| DeepSeek | P2 | ✅ | — | — | ✅ | ✅ |
| Together AI | P3 | ✅ | — | — | — | ✅ |
| Groq | P3 | ✅ | — | — | — | ✅ |
| Mistral AI | P3 | ✅ | — | — | — | ✅ |
| Fireworks AI | P3 | ✅ | — | — | — | ✅ |
| Morph | P3 | ✅ | — | — | — | ✅ |
| Refuseless | P3 | ✅ | — | — | ✅ | ✅ |
| OpenCode | P3 | ✅ | — | — | — | ✅ |

`—` means the provider does not expose that capability through the supported official public API. A provider failing never stops other accounts from synchronizing.

## Technology Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide, React Router, TanStack Query |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic, HTTPX |
| Database | SQLite, UTC timestamps, idempotent synchronization |
| Testing | Pytest, Vitest, React Testing Library, respx |
| Delivery | GitHub Actions, Docker Compose (optional) |

## Quick Start — Local Development

### Prerequisites

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+ and npm

### One command

```bash
cp .env.example .env
./scripts/start_local.sh
```

Then open:

- Dashboard: <http://127.0.0.1:5173>
- API: <http://127.0.0.1:8000>
- OpenAPI docs: <http://127.0.0.1:8000/docs>

The script runs the Alembic migration, starts FastAPI on `127.0.0.1:8000`, and starts Vite on `127.0.0.1:5173`.

### Manual startup

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Open <http://127.0.0.1:5173>. SQLite data is persisted in the local `data/` directory, which is intentionally ignored by Git.

## Testing and Quality Checks

```bash
uv run pytest
uv run ruff check backend connectors tests

cd frontend
npm test
npm run build
```

## Adding a Provider Connector

Connectors are isolated from persistence and return normalized DTOs. To add one:

1. Create `connectors/<provider_id>/__init__.py`.
2. Inherit from `BaseConnector` in `connectors/base/interface.py`.
3. Declare capabilities conservatively in `get_capabilities()` based on official documentation.
4. Implement only documented endpoints for `test_connection`, `fetch_usage`, `fetch_costs`, `fetch_balance`, and/or `fetch_model_pricing`.
5. Add the provider's official API hostname to `APPROVED_PROVIDER_HOSTS` in `connectors/base/http_client.py`.
6. Register the connector in `connectors/registry.py`.
7. Add provider metadata and capability tests under `tests/connectors/` using mocked HTTP responses; never require real API keys in tests.
8. Update `docs/PROVIDER_CAPABILITIES.md` and this README.

Connectors **must not** import SQLAlchemy models or access the database. The backend owns persistence, deduplication, estimation, currency conversion, and synchronization.

## Security and Data Model

- API keys are encrypted with Fernet; the local master key is stored at `data/.secret.key` with restrictive permissions when `MYAISTATS_SECRET_KEY` is not configured.
- Outbound requests require HTTPS and an approved provider host; redirects are disabled and timeouts are enforced.
- Credentials, SQLite files, backups, `.env`, `node_modules/`, and `.venv/` are excluded by `.gitignore`.
- Original currencies are retained; conversions use stored exchange rates and dates.

Read the complete security assumptions in [`docs/SECURITY.md`](docs/SECURITY.md).

## Project Structure

```text
frontend/       React dashboard
backend/app/    FastAPI API, SQLAlchemy models, services, sync worker
connectors/     Independent official provider adapters
migrations/     Alembic migrations
tests/          Backend, connector, and frontend tests
docs/           Capability and security documentation
scripts/        Local startup helpers
```

## Contributing and License

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for architectural and privacy requirements. MyAIStats is released under the [MIT License](LICENSE).
