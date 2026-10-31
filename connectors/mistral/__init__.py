"""Mistral AI Official Connector."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

MISTRAL_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="mistral-large-latest",
        display_name="Mistral Large 2",
        context_window=128000,
        input_price_per_million=2.00,
        output_price_per_million=6.00,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="codestral-latest",
        display_name="Codestral",
        context_window=256000,
        input_price_per_million=0.30,
        output_price_per_million=0.90,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
]


class MistralConnector(BaseConnector):
    provider_id = "mistral"
    provider_name = "Mistral AI"
    category_priority = 3
    api_base_url = "https://api.mistral.ai"
    docs_url = "https://docs.mistral.ai/api/"
    auth_instructions = (
        "Provide a Mistral La Plateforme API key. Connection testing uses GET /v1/models. "
        "Mistral does not expose historical usage, billing, or balance endpoints via public REST API."
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
                "Supports connection verification (/v1/models) and official model pricing catalog. "
                "Usage, costs, and balances are not exposed via public API."
            ),
        )

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/models",
            headers={"Authorization": f"Bearer {creds.api_key.strip()}"},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to Mistral AI API (/v1/models verified).",
                detected_models_count=len(data),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Mistral AI authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="Mistral AI does not expose account balances via a public API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(MISTRAL_OFFICIAL_PRICING)
