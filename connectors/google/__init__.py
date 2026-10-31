"""Google Gemini Official Connector."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

GEMINI_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        context_window=1048576,
        input_price_per_million=0.10,
        output_price_per_million=0.40,
        cached_input_price_per_million=0.025,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        context_window=2097152,
        input_price_per_million=1.25,
        output_price_per_million=5.00,
        cached_input_price_per_million=0.3125,
        currency="USD",
        price_source="official_catalog",
    ),
]


class GoogleGeminiConnector(BaseConnector):
    provider_id = "google"
    provider_name = "Google Gemini"
    category_priority = 2
    api_base_url = "https://generativelanguage.googleapis.com"
    docs_url = "https://ai.google.dev/gemini-api/docs/models/gemini"
    auth_instructions = (
        "Provide a Google AI Studio Gemini API key. Connection testing and model catalog discovery use "
        "GET /v1beta/models with x-goog-api-key header. Historical billing and token usage are managed in "
        "Google Cloud Billing / Cloud Monitoring and are not exposed via a simple Gemini API key REST endpoint."
    )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_connection_test=True,
            supports_usage=False,
            supports_costs=False,
            supports_balance=False,
            supports_pricing=True,
            requires_admin_key_for_usage=False,
            capability_notes=(
                "Google AI Studio API keys support connection testing (/v1beta/models) and model pricing. "
                "Usage, billing, and balance require Google Cloud Billing BigQuery export and are not exposed via Gemini API key."
            ),
        )

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1beta/models",
            headers={"x-goog-api-key": creds.api_key.strip()},
        )
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to Google Gemini API (/v1beta/models verified).",
                detected_models_count=len(models),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Google Gemini authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="Google Gemini API does not expose account balances via API key.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(GEMINI_OFFICIAL_PRICING)
