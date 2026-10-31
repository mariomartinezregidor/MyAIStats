"""Groq Official Connector."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

GROQ_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="llama-3.3-70b-versatile",
        display_name="Groq: Llama 3.3 70B Versatile",
        context_window=128000,
        input_price_per_million=0.59,
        output_price_per_million=0.79,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="llama-3.1-8b-instant",
        display_name="Groq: Llama 3.1 8B Instant",
        context_window=128000,
        input_price_per_million=0.05,
        output_price_per_million=0.08,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
]


class GroqConnector(BaseConnector):
    provider_id = "groq"
    provider_name = "Groq"
    category_priority = 3
    api_base_url = "https://api.groq.com"
    docs_url = "https://console.groq.com/docs/api-reference#models"
    auth_instructions = (
        "Provide a GroqCloud API key (gsk_...). Connection testing uses GET /openai/v1/models. "
        "Groq does not currently expose historical usage, billing, or credit balances via a public REST API."
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
                "Supports connection verification (/openai/v1/models) and official model pricing catalog. "
                "Usage, costs, and balances are not exposed via public API."
            ),
        )

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/openai/v1/models",
            headers={"Authorization": f"Bearer {creds.api_key.strip()}"},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to GroqCloud API (/openai/v1/models verified).",
                detected_models_count=len(data),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Groq authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="Groq does not expose account balances via a public API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(GROQ_OFFICIAL_PRICING)
