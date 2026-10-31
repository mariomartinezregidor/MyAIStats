# Provider Capabilities & Official API Verification

MyAIStats strictly queries **documented, official provider REST endpoints** over HTTPS. It never scrapes web consoles, never uses browser session cookies, and never invents unsupported metrics.

## Capability Matrix

| Provider | Priority | Connection Test | Token Usage API | Official Costs API | Confirmed Balance API | Model Pricing | Key Requirements & Notes |
| --- | :---: | :---: | :---: | :---: | :---: | :---: | --- |
| **OpenAI** | P1 | Yes (`/v1/models`) | Yes (`/v1/organization/usage/completions`) | Yes (`/v1/organization/costs`) | **Unsupported** | Yes | Organization Usage & Costs require an **Organization Admin API Key** (`sk-admin-...`). Standard project keys (`sk-proj-...`) can test connection and list models. OpenAI does not expose prepaid balance via a public API. |
| **OpenRouter** | P1 | Yes (`/api/v1/auth/key`) | Yes (`/api/v1/activity`) | Yes (`/api/v1/activity`) | **Yes** (`/api/v1/credits`) | Yes (`/api/v1/models`) | Full support for confirmed available credits, per-model activity, and live pricing. |
| **Anthropic** | P2 | Yes (`/v1/models`) | Yes (`/v1/organizations/usage_report/messages`) | Yes (`/v1/organizations/cost_report`) | **Unsupported** | Yes | Usage & Cost reports require an **Anthropic Admin API Key** (`sk-ant-admin...`). Prepaid balances are not exposed via public API. |
| **Google Gemini** | P2 | Yes (`/v1beta/models`) | **Unsupported** | **Unsupported** | **Unsupported** | Yes | Gemini AI Studio API keys authenticate via `x-goog-api-key` and verify model access. Billing and usage require Google Cloud Billing / BigQuery export. |
| **DeepSeek** | P2 | Yes (`/user/balance`) | **Unsupported** | **Unsupported** | **Yes** (`/user/balance`) | Yes | Confirmed account balance (`total_balance`, `granted_balance`, `topped_up_balance`) in USD/CNY is officially supported via `GET /user/balance`. |
| **Together AI** | P3 | Yes (`/v1/models`) | **Unsupported** | **Unsupported** | **Unsupported** | Yes | Connection verification and model catalog via `/v1/models`. |
| **Groq** | P3 | Yes (`/openai/v1/models`) | **Unsupported** | **Unsupported** | **Unsupported** | Yes | Connection verification and model catalog via `/openai/v1/models`. |
| **Mistral AI** | P3 | Yes (`/v1/models`) | **Unsupported** | **Unsupported** | **Unsupported** | Yes | Connection verification and model catalog via `/v1/models`. |
| **Fireworks AI** | P3 | Yes (`/inference/v1/models`) | **Unsupported** | **Unsupported** | **Unsupported** | Yes | Connection verification and model catalog via `/inference/v1/models`. |
