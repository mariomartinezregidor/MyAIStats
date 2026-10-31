"""Fireworks AI Official Connector."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

FIREWORKS_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="accounts/fireworks/models/deepseek-v3",
        display_name="Fireworks: DeepSeek V3",
        context_window=128000,
        input_price_per_million=0.90,
        output_price_per_million=0.90,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="accounts/fireworks/models/llama-v3p3-70b-instruct",
        display_name="Fireworks: Llama 3.3 70B Instruct",
        context_window=131072,
        input_price_per_million=0.90,
        output_price_per_million=0.90,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
]


class FireworksConnector(BaseConnector):
    provider_id = "fireworks"
    provider_name = "Fireworks AI"
    category_priority = 3
    api_base_url = "https://api.fireworks.ai"
    docs_url = "https://docs.fireworks.ai/api-reference/list-models"
    auth_instructions = (
        "Provide a Fireworks AI API key (fw_...). Connection testing uses GET /inference/v1/models. "
        "Fireworks AI does not expose historical usage, billing, or balance endpoints via public REST API."
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
                "Supports connection verification (/inference/v1/models) and official model pricing catalog. "
                "Usage, costs, and balances are not exposed via public API."
            ),
        )

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/inference/v1/models",
            headers={"Authorization": f"Bearer {creds.api_key.strip()}"},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to Fireworks AI API (/inference/v1/models verified).",
                detected_models_count=len(data),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Fireworks AI authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="Fireworks AI does not expose account balances via a public API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(FIREWORKS_OFFICIAL_PRICING)
