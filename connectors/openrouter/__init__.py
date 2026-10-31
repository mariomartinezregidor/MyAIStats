"""OpenRouter Official Connector."""

from datetime import UTC, datetime

from connectors.base.interface import BaseConnector
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedCostRecord,
    NormalizedModelPrice,
    NormalizedUsageRecord,
    ProviderCapabilities,
)

OPENROUTER_FALLBACK_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="openai/gpt-4o",
        display_name="OpenRouter: GPT-4o",
        context_window=128000,
        input_price_per_million=2.50,
        output_price_per_million=10.00,
        cached_input_price_per_million=1.25,
        currency="USD",
        price_source="official_api",
    ),
    NormalizedModelPrice(
        model_id="anthropic/claude-3.5-sonnet",
        display_name="OpenRouter: Claude 3.5 Sonnet",
        context_window=200000,
        input_price_per_million=3.00,
        output_price_per_million=15.00,
        cached_input_price_per_million=0.30,
        currency="USD",
        price_source="official_api",
    ),
]


class OpenRouterConnector(BaseConnector):
    provider_id = "openrouter"
    provider_name = "OpenRouter"
    category_priority = 1
    api_base_url = "https://openrouter.ai"
    docs_url = "https://openrouter.ai/docs/api-reference/limits"
    auth_instructions = (
        "Provide an OpenRouter API key (sk-or-v1-...) or Provisioning API key. "
        "OpenRouter officially exposes credit balances via GET /api/v1/credits, "
        "per-model activity via GET /api/v1/activity, and live model pricing via GET /api/v1/models."
    )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_connection_test=True,
            supports_usage=True,
            supports_costs=True,
            supports_balance=True,
            supports_pricing=True,
            requires_admin_key_for_usage=False,
            capability_notes=(
                "Full support for confirmed credit balances (/api/v1/credits), "
                "live model pricing (/api/v1/models), and usage/cost activity (/api/v1/activity)."
            ),
        )

    def _headers(self, creds: ConnectorCredentials) -> dict[str, str]:
        return {"Authorization": f"Bearer {creds.api_key.strip()}"}

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/api/v1/auth/key",
            headers=self._headers(creds),
        )
        if resp.status_code == 200:
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected to OpenRouter API (/api/v1/auth/key verified).",
                is_admin_key=True,
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"OpenRouter authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/api/v1/credits",
            headers=self._headers(creds),
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            total_credits = float(data.get("total_credits") or 0.0)
            total_usage = float(data.get("total_usage") or 0.0)
            available = max(0.0, round(total_credits - total_usage, 6))
            return NormalizedBalanceSnapshot(
                available_balance=available,
                total_credits=total_credits,
                used_credits=total_usage,
                currency="USD",
                is_supported=True,
                status_note="Confirmed via OpenRouter /api/v1/credits",
                data_source="official_api",
            )

        # Fallback check on /api/v1/auth/key
        key_resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/api/v1/auth/key",
            headers=self._headers(creds),
        )
        if key_resp.status_code == 200:
            data = key_resp.json().get("data", {})
            limit_rem = data.get("limit_remaining")
            usage = float(data.get("usage") or 0.0)
            if limit_rem is not None:
                return NormalizedBalanceSnapshot(
                    available_balance=float(limit_rem),
                    total_credits=float(data.get("limit") or 0.0),
                    used_credits=usage,
                    currency="USD",
                    is_supported=True,
                    status_note="Confirmed key limit remaining via /api/v1/auth/key",
                    data_source="official_api",
                )
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=True,
            status_note=f"OpenRouter credits endpoint returned HTTP {resp.status_code}.",
            data_source="official_api",
        )

    async def fetch_usage(
        self,
        creds: ConnectorCredentials,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedUsageRecord]:
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/api/v1/activity",
            headers=self._headers(creds),
        )
        records: list[NormalizedUsageRecord] = []
        if resp.status_code != 200:
            return records

        payload = resp.json()
        items = payload.get("data", []) if isinstance(payload, dict) else []
        for idx, item in enumerate(items):
            date_str = item.get("date")
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                except ValueError:
                    dt = datetime.now(UTC)
            else:
                dt = datetime.now(UTC)

            if dt < start_time or dt > end_time:
                continue

            model_id = item.get("model") or "openrouter/auto"
            in_tok = int(item.get("prompt_tokens") or 0)
            out_tok = int(item.get("completion_tokens") or 0)
            cached_tok = int(item.get("cached_tokens") or 0)
            reqs = int(item.get("requests") or 1)
            usage_cost = float(item.get("usage") or 0.0)
            ext_id = f"openrouter-activity-{dt.strftime('%Y-%m-%d')}-{model_id}-{idx}"
            records.append(
                NormalizedUsageRecord(
                    model_id=model_id,
                    timestamp=dt,
                    period_start=dt,
                    period_end=dt,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cached_input_tokens=cached_tok,
                    total_tokens=in_tok + out_tok,
                    requests_count=reqs,
                    currency="USD",
                    actual_cost=usage_cost if usage_cost > 0 else None,
                    data_source="official_api",
                    data_precision="bucket_1d",
                    external_record_id=ext_id,
                )
            )
        return records

    async def fetch_costs(
        self,
        creds: ConnectorCredentials,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedCostRecord]:
        usage_rows = await self.fetch_usage(creds, start_time, end_time)
        costs: list[NormalizedCostRecord] = []
        for row in usage_rows:
            if row.actual_cost is not None and row.actual_cost > 0:
                costs.append(
                    NormalizedCostRecord(
                        model_id=row.model_id,
                        period_start=row.period_start,
                        period_end=row.period_end,
                        amount=row.actual_cost,
                        currency=row.currency,
                        cost_type="actual",
                        data_source="official_billing_api",
                        external_record_id=f"cost-{row.external_record_id}",
                    )
                )
        return costs

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        try:
            resp = await self.http.request(
                "GET",
                f"{self.api_base_url}/api/v1/models",
            )
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                prices: list[NormalizedModelPrice] = []
                for item in data[:40]:
                    pricing = item.get("pricing") or {}
                    prompt_per_tok = float(pricing.get("prompt") or 0.0)
                    completion_per_tok = float(pricing.get("completion") or 0.0)
                    if prompt_per_tok <= 0 and completion_per_tok <= 0:
                        continue
                    prices.append(
                        NormalizedModelPrice(
                            model_id=item.get("id", "unknown"),
                            display_name=item.get("name") or item.get("id", "Unknown"),
                            context_window=item.get("context_length"),
                            input_price_per_million=round(prompt_per_tok * 1_000_000, 4),
                            output_price_per_million=round(completion_per_tok * 1_000_000, 4),
                            cached_input_price_per_million=None,
                            currency="USD",
                            price_source="official_api",
                        )
                    )
                if prices:
                    return prices
        except Exception:
            pass
        return list(OPENROUTER_FALLBACK_PRICING)
