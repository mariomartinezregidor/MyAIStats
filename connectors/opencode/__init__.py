"""OpenCode Official Connector (opencode.ai)."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

OPENCODE_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="kimi-k3",
        display_name="OpenCode: Kimi K3",
        context_window=1048576,
        input_price_per_million=3.00,
        output_price_per_million=15.00,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="glm-5.3",
        display_name="OpenCode: GLM-5.3",
        context_window=1048576,
        input_price_per_million=1.19,
        output_price_per_million=6.00,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="glm-5.3-flash",
        display_name="OpenCode: GLM-5.3-Flash",
        context_window=1048576,
        input_price_per_million=0.20,
        output_price_per_million=0.70,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="gpt-6.1-sol",
        display_name="OpenCode: GPT 6.1 Sol",
        context_window=1100000,
        input_price_per_million=2.00,
        output_price_per_million=10.00,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="gpt-6-luna",
        display_name="OpenCode: GPT 6 Luna",
        context_window=1100000,
        input_price_per_million=0.10,
        output_price_per_million=0.50,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="minimax-m3",
        display_name="OpenCode: MiniMax M3",
        context_window=512000,
        input_price_per_million=0.30,
        output_price_per_million=1.00,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="claude-sonnet-5-5",
        display_name="OpenCode: Claude Sonnet 5.5",
        context_window=200000,
        input_price_per_million=3.00,
        output_price_per_million=15.00,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
]


class OpenCodeConnector(BaseConnector):
    provider_id = "opencode"
    provider_name = "OpenCode"
    category_priority = 3
    api_base_url = "https://opencode.ai/inference"
    docs_url = "https://opencode.ai/v2/docs/console/api/inference"
    auth_instructions = (
        "Provide an OpenCode personal or service account API key. Connection testing uses "
        "GET /inference/v1/models. OpenCode serves OpenAI, Anthropic, and Gemini-compatible APIs. "
        "Historical usage, billing, and Go subscription balances are managed in the OpenCode Console "
        "and are not exposed via a simple public REST endpoint."
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

    def _headers(self, creds: ConnectorCredentials) -> dict[str, str]:
        return {"Authorization": f"Bearer {creds.api_key.strip()}"}

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/models",
            headers=self._headers(creds),
        )
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", []) if isinstance(data, dict) else []
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to OpenCode Inference API (/inference/v1/models verified).",
                detected_models_count=len(models),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"OpenCode authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="OpenCode does not expose account balances via a public API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(OPENCODE_OFFICIAL_PRICING)
