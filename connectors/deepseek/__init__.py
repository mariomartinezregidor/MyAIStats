"""DeepSeek Official Connector."""

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedModelPrice,
    ProviderCapabilities,
)

DEEPSEEK_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="deepseek-chat",
        display_name="DeepSeek V3 (deepseek-chat)",
        context_window=64000,
        input_price_per_million=0.27,
        output_price_per_million=1.10,
        cached_input_price_per_million=0.07,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="deepseek-reasoner",
        display_name="DeepSeek R1 (deepseek-reasoner)",
        context_window=64000,
        input_price_per_million=0.55,
        output_price_per_million=2.19,
        cached_input_price_per_million=0.14,
        currency="USD",
        price_source="official_catalog",
    ),
]


class DeepSeekConnector(BaseConnector):
    provider_id = "deepseek"
    provider_name = "DeepSeek"
    category_priority = 2
    api_base_url = "https://api.deepseek.com"
    docs_url = "https://api-docs.deepseek.com/api/get-user-balance"
    auth_instructions = (
        "Provide a DeepSeek API key. DeepSeek officially exposes confirmed account balances (in USD or CNY) "
        "via GET https://api.deepseek.com/user/balance and model listing via GET /models. "
        "Historical per-request token usage is not exposed via an official REST endpoint."
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
                "Confirmed balance is officially supported via GET /user/balance. "
                "Historical token usage logs are not exposed via DeepSeek public REST API."
            ),
        )

    def _headers(self, creds: ConnectorCredentials) -> dict[str, str]:
        return {"Authorization": f"Bearer {creds.api_key.strip()}"}

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/user/balance",
            headers=self._headers(creds),
        )
        if resp.status_code == 200:
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to DeepSeek API (/user/balance verified).",
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"DeepSeek authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/user/balance",
            headers=self._headers(creds),
        )
        if resp.status_code == 200:
            payload = resp.json()
            infos = payload.get("balance_infos") or []
            if infos:
                # Prefer USD if present, else first entry
                chosen = next(
                    (b for b in infos if (b.get("currency") or "").upper() == "USD"),
                    infos[0],
                )
                total_bal = float(chosen.get("total_balance") or 0.0)
                granted = float(chosen.get("granted_balance") or 0.0)
                topped_up = float(chosen.get("topped_up_balance") or 0.0)
                currency = (chosen.get("currency") or "USD").upper()
                return NormalizedBalanceSnapshot(
                    available_balance=total_bal,
                    total_credits=granted + topped_up if (granted + topped_up) > 0 else total_bal,
                    used_credits=None,
                    currency=currency,
                    is_supported=True,
                    status_note="Confirmed via DeepSeek GET /user/balance",
                    data_source="official_api",
                )
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=True,
            status_note=f"DeepSeek balance endpoint returned HTTP {resp.status_code}.",
            data_source="official_api",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(DEEPSEEK_OFFICIAL_PRICING)
