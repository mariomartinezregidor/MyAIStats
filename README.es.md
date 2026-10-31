# MyAIStats (v0.2.0)

**All your AI usage. One dashboard.**

[![CI](https://github.com/mariomartinezregidor/MyAIStats/actions/workflows/ci.yml/badge.svg)](https://github.com/mariomartinezregidor/MyAIStats/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/version-v0.2.1-blue.svg)](https://github.com/mariomartinezregidor/MyAIStats/releases/tag/v0.2.1)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Local-first](https://img.shields.io/badge/privacy-local--first-purple.svg)](docs/SECURITY.md)

MyAIStats es una aplicación open-source y local-first para centralizar el uso de APIs de IA, tokens, costes, créditos, saldos y precios de modelos desde un único panel privado. Se ejecuta en tu máquina, no requiere registro y mantiene las credenciales y el historial local.

> **v0.2.1** — añade soporte de idioma español (i18n) y README en español.

[English version](README.md)

## Por qué MyAIStats

- **Privacidad local-first** — el backend se vincula a `127.0.0.1`; las credenciales se cifran en reposo con Fernet y nunca se devuelven al frontend.
- **Precisión financiera** — los costes facturados reales y los estimados permanecen separados, con etiquetas explícitas y sin doble conteo.
- **Solo saldos confirmados** — las APIs de saldo no soportadas se marcan claramente en lugar de adivinarse.
- **Soporte multi-cuenta** — conecta varias cuentas del mismo proveedor.
- **Analítica** — gasto diario/mensual, comparativas por proveedor/modelo, consumo de tokens, historial de saldos y auditoría.
- **Exportación y propiedad** — exportaciones CSV/JSON más copia de seguridad y restauración de SQLite.
- **Modo Demo** — registros realistas etiquetados como `[DEMO]` para explorar la interfaz antes de conectar cuentas.

## Conectores soportados

Las capacidades se basan únicamente en APIs oficiales documentadas. Consulta [`docs/PROVIDER_CAPABILITIES.md`](docs/PROVIDER_CAPABILITIES.md) para detalles de autenticación, permisos y endpoints.

| Proveedor | Prioridad | Conexión | Uso | Costes | Saldo | Precios |
| --- | :---: | :---: | :---: | :---: | :---: | :---: |
| OpenAI | P1 | ✅ | ✅ Clave admin | ✅ Clave admin | — | ✅ |
| OpenRouter | P1 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Anthropic | P2 | ✅ | ✅ Clave admin | ✅ Clave admin | — | ✅ |
| Google Gemini | P2 | ✅ | — | — | — | ✅ |
| DeepSeek | P2 | ✅ | — | — | ✅ | ✅ |
| Together AI | P3 | ✅ | — | — | — | ✅ |
| Groq | P3 | ✅ | — | — | — | ✅ |
| Mistral AI | P3 | ✅ | — | — | — | ✅ |
| Fireworks AI | P3 | ✅ | — | — | — | ✅ |
| Morph | P3 | ✅ | — | — | — | ✅ |
| Refuseless | P3 | ✅ | — | — | ✅ | ✅ |
| OpenCode | P3 | ✅ | — | — | — | ✅ |

`—` significa que el proveedor no expone esa capacidad mediante su API pública oficial. Un proveedor que falla nunca detiene la sincronización de los demás.

## Stack tecnológico

| Capa | Tecnologías |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts, Lucide, React Router, TanStack Query |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic, HTTPX |
| Base de datos | SQLite, marcas de tiempo UTC, sincronización idempotente |
| Testing | Pytest, Vitest, React Testing Library, respx |
| Entrega | GitHub Actions, Docker Compose (opcional) |

## Inicio rápido — Desarrollo local

### Requisitos previos

- Python 3.11+ y [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+ y npm

### Un solo comando

```bash
cp .env.example .env
./scripts/start_local.sh
```

Luego abre:

- Panel: <http://127.0.0.1:5173>
- API: <http://127.0.0.1:8000>
- Documentación OpenAPI: <http://127.0.0.1:8000/docs>

El script ejecuta la migración de Alembic, inicia FastAPI en `127.0.0.1:8000` y Vite en `127.0.0.1:5173`.

### Inicio manual

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

En otra terminal:

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

Abre <http://127.0.0.1:5173>. Los datos de SQLite se persisten en el directorio local `data/`, que está ignorado por Git.

## Pruebas y calidad

```bash
uv run pytest
uv run ruff check backend connectors tests

cd frontend
npm test
npm run build
```

## Añadir un conector de proveedor

Los conectores están aislados de la persistencia y devuelven DTOs normalizados. Para añadir uno:

1. Crea `connectors/<provider_id>/__init__.py`.
2. Hereda de `BaseConnector` en `connectors/base/interface.py`.
3. Declara las capacidades de forma conservadora en `get_capabilities()` según la documentación oficial.
4. Implementa únicamente los endpoints documentados para `test_connection`, `fetch_usage`, `fetch_costs`, `fetch_balance` y/o `fetch_model_pricing`.
5. Añade el nombre de host oficial de la API del proveedor a `APPROVED_PROVIDER_HOSTS` en `connectors/base/http_client.py`.
6. Registra el conector en `connectors/registry.py`.
7. Añade metadatos del proveedor y tests de capacidad en `tests/connectors/` usando respuestas HTTP simuladas; nunca requieras claves de API reales en los tests.
8. Actualiza `docs/PROVIDER_CAPABILITIES.md` y este README.

Los conectores **no deben** importar modelos de SQLAlchemy ni acceder a la base de datos. El backend se encarga de la persistencia, deduplicación, estimación, conversión de moneda y sincronización.

## Seguridad y modelo de datos

- Las claves de API se cifran con Fernet; la clave maestra local se almacena en `data/.secret.key` con permisos restrictivos cuando no se configura `MYAISTATS_SECRET_KEY`.
- Las peticiones salientes requieren HTTPS y un host de proveedor aprobado; las redirecciones están desactivadas y se aplican tiempos de espera.
- Las credenciales, archivos SQLite, copias de seguridad, `.env`, `node_modules/` y `.venv/` están excluidos por `.gitignore`.
- Las monedas originales se conservan; las conversiones usan tipos de cambio y fechas almacenados.

Lee las asunciones de seguridad completas en [`docs/SECURITY.md`](docs/SECURITY.md).

## Estructura del proyecto

```text
frontend/       Panel de control React
backend/app/    API FastAPI, modelos SQLAlchemy, servicios, worker de sincronización
connectors/     Adaptadores independientes de proveedores oficiales
migrations/     Migraciones de Alembic
tests/          Tests de backend, conectores y frontend
docs/           Documentación de capacidades y seguridad
scripts/        Ayudantes de inicio local
```

## Idiomas

La interfaz soporta **inglés** y **español**. El idioma por defecto es inglés; puedes cambiarlo desde el selector de la barra superior o en Ajustes. La preferencia se guarda en el navegador.

## Contribución y licencia

Consulta [`CONTRIBUTING.md`](CONTRIBUTING.md) para los requisitos arquitectónicos y de privacidad. MyAIStats se publica bajo la [Licencia MIT](LICENSE).