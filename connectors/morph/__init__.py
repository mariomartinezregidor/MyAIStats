"""Morph Official Connector (morphllm.com)."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

MORPH_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="morph-glm53-744b",
        display_name="Morph: GLM-5.3 744B",
        context_window=1048576,
        input_price_per_million=1.19,
        output_price_per_million=6.00,
        cached_input_price_per_million=0.12,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="morph-glm53flash",
        display_name="Morph: GLM-5.3-Flash",
        context_window=1048576,
        input_price_per_million=0.20,
        output_price_per_million=0.70,
        cached_input_price_per_million=0.02,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="morph-dsv41flash",
        display_name="Morph: DeepSeek V4.1 Flash",
        context_window=1048576,
        input_price_per_million=0.12,
        output_price_per_million=0.80,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="morph-dsv4flash",
        display_name="Morph: DeepSeek V4 Flash 0731",
        context_window=1048576,
        input_price_per_million=0.142,
        output_price_per_million=0.3996,
        cached_input_price_per_million=0.018,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="morph-kimik3",
        display_name="Morph: Kimi K3",
        context_window=1048576,
        input_price_per_million=2.50,
        output_price_per_million=14.00,
        cached_input_price_per_million=0.145,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="morph-kimik3-fast",
        display_name="Morph: Kimi K3 Fast",
        context_window=1048576,
        input_price_per_million=6.00,
        output_price_per_million=22.50,
        cached_input_price_per_million=0.145,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="morph-v3-fast",
        display_name="Morph V3 Fast",
        context_window=262144,
        input_price_per_million=0.80,
        output_price_per_million=1.20,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="morph-v3-large",
        display_name="Morph V3 Large",
        context_window=262144,
        input_price_per_million=0.90,
        output_price_per_million=1.90,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
]


class MorphConnector(BaseConnector):
    provider_id = "morph"
    provider_name = "Morph"
    category_priority = 3
    api_base_url = "https://api.morphllm.com"
    docs_url = "https://docs.morphllm.com/introduction"
    auth_instructions = (
        "Provide a Morph API key. Connection testing and model listing use GET /v1/models "
        "with x-api-key or Authorization: Bearer. Morph serves open-weight models on an "
        "OpenAI-compatible API. Historical usage, billing, and balance are not exposed via a public REST API."
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

    def _headers(self, creds: ConnectorCredentials) -> dict[str, str]:
        return {
            "x-api-key": creds.api_key.strip(),
            "Authorization": f"Bearer {creds.api_key.strip()}",
        }

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
                message="Connected to Morph API (/v1/models verified).",
                detected_models_count=len(models),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Morph authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="Morph does not expose account balances via a public API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(MORPH_OFFICIAL_PRICING)
