# Contributing to MyAIStats

Thank you for your interest in contributing to **MyAIStats**!

## Core Principles

1. **Local-First & Privacy-Preserving**: User API keys, credentials, and financial data must never leave the user's machine except to query official provider endpoints directly.
2. **Official APIs Only**: Never scrape web pages, use browser session cookies, or rely on undocumented internal APIs.
3. **Strict Financial Accuracy**:
   - Never mix **Actual Billed Costs** with **Estimated Costs**.
   - Never fabricate or guess **Available Balances**. If an official API does not expose balance information, mark `supports_balance = False`.
   - Preserve original currency values (`USD`, `EUR`) and record exchange rates explicitly when converting.
4. **Connector Isolation**: Provider connectors in `connectors/` must only handle external HTTP communication and return normalized data models. Connectors must never import or touch SQLAlchemy database sessions directly.

## Development Setup

### Prerequisites
- Python 3.12+ (managed with `uv` or `venv`)
- Node.js 20+ & npm

### Running Backend Tests
```bash
uv run pytest
```

### Running Frontend Tests
```bash
cd frontend
npm test
```

## Adding a New Provider Connector

1. Create a directory under `connectors/<provider_id>/`.
2. Inherit from `BaseConnector` in `connectors/base/interface.py`.
3. Add the allowed API hostname to the SSRF allowlist in `connectors/base/http_client.py`.
4. Declare accurate `ProviderCapabilities` based strictly on official documentation.
5. Add unit tests with mocked HTTP responses under `tests/connectors/`.
