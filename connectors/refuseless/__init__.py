"""Refuseless Official Connector (refuseless.com)."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

REFUSELESS_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="glm-5.3-abliterated",
        display_name="Refuseless: GLM 5.3 Abliterated",
        context_window=1048576,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="glm-5.3-flash-abliterated",
        display_name="Refuseless: GLM 5.3 Flash Abliterated",
        context_window=1048576,
        input_price_per_million=0.0,
        output_price_per_million=0.0,
        cached_input_price_per_million=None,
        currency="USD",
        price_source="official_catalog",
    ),
]


class RefuselessConnector(BaseConnector):
    provider_id = "refuseless"
    provider_name = "Refuseless"
    category_priority = 3
    api_base_url = "https://api.refuseless.com"
    docs_url = "https://docs.refuseless.com/introduction"
    auth_instructions = (
        "Provide a Refuseless API key (rk-...). Connection testing uses GET /v1/models. "
        "Confirmed credit balance is available via GET /v1/credits. "
        "Refuseless hosts abliterated open-weight models behind an OpenAI-compatible API. "
        "Historical token usage and billing are not exposed via a public REST API."
    )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_connection_test=True,
            supports_usage=False,
            supports_costs=False,
            supports_balance=True,
            supports_pricing=True,
            requires_admin_key_for_usage=False,
            capability_notes=(
                "Supports connection verification (/v1/models) and confirmed credit balance (/v1/credits). "
                "Usage, costs, and model pricing catalog are not published via official API."
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
                message="Connected to Refuseless API (/v1/models verified).",
                detected_models_count=len(models),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Refuseless authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/credits",
            headers=self._headers(creds),
        )
        if resp.status_code == 200:
            data = resp.json()
            # Refuseless returns credit balance; support both common shapes
            balance = None
            if isinstance(data, dict):
                balance = data.get("balance") or data.get("credits") or data.get("available_credits")
                if balance is None and isinstance(data.get("data"), dict):
                    balance = data["data"].get("balance") or data["data"].get("credits")
            try:
                balance_val = float(balance) if balance is not None else None
            except (TypeError, ValueError):
                balance_val = None
            return NormalizedBalanceSnapshot(
                available_balance=balance_val,
                total_credits=balance_val,
                used_credits=None,
                currency="USD",
                is_supported=True,
                status_note="Confirmed via Refuseless GET /v1/credits",
                data_source="official_api",
            )
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=True,
            status_note=f"Refuseless credits endpoint returned HTTP {resp.status_code}.",
            data_source="official_api",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(REFUSELESS_OFFICIAL_PRICING)
