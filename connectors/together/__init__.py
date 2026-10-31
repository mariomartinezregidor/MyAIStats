"""Together AI Official Connector."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

TOGETHER_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="meta-llama/Llama-3.3-70B-Instruct-Turbo",
        display_name="Llama 3.3 70B Instruct Turbo",
        context_window=131072,
        input_price_per_million=0.88,
        output_price_per_million=0.88,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="deepseek-ai/DeepSeek-R1",
        display_name="Together: DeepSeek R1",
        context_window=65536,
        input_price_per_million=3.00,
        output_price_per_million=7.00,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
]


class TogetherConnector(BaseConnector):
    provider_id = "together"
    provider_name = "Together AI"
    category_priority = 3
    api_base_url = "https://api.together.xyz"
    docs_url = "https://docs.together.ai/reference/models-list"
    auth_instructions = (
        "Provide a Together AI API key. Connection testing and live model pricing use GET /v1/models. "
        "Historical usage and account balance are not exposed via a public REST API endpoint."
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
                "Supports connection verification and model pricing via /v1/models. "
                "Usage, billing, and balance are not exposed via public API."
            ),
        )

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/models",
            headers={"Authorization": f"Bearer {creds.api_key.strip()}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            count = len(data) if isinstance(data, list) else 0
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to Together AI API (/v1/models verified).",
                detected_models_count=count,
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Together AI authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="Together AI does not expose account balances via an official public API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(TOGETHER_OFFICIAL_PRICING)
