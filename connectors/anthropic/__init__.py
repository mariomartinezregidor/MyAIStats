"""Anthropic Official Connector."""

from datetime import UTC, datetime
from typing import Any

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

ANTHROPIC_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="claude-3-7-sonnet-20250219",
        display_name="Claude 3.7 Sonnet",
        context_window=200000,
        input_price_per_million=3.00,
        output_price_per_million=15.00,
        cached_input_price_per_million=0.30,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        context_window=200000,
        input_price_per_million=3.00,
        output_price_per_million=15.00,
        cached_input_price_per_million=0.30,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="claude-3-5-haiku-20241022",
        display_name="Claude 3.5 Haiku",
        context_window=200000,
        input_price_per_million=0.80,
        output_price_per_million=4.00,
        cached_input_price_per_million=0.08,
        currency="USD",
        price_source="official_catalog",
    ),
]


class AnthropicConnector(BaseConnector):
    provider_id = "anthropic"
    provider_name = "Anthropic"
    category_priority = 2
    api_base_url = "https://api.anthropic.com"
    docs_url = "https://docs.anthropic.com/en/api/admin-api"
    auth_instructions = (
        "Standard Anthropic keys (sk-ant-api03-...) support connection verification via GET /v1/models. "
        "Organization usage (/v1/organizations/usage_report/messages) and cost reports "
        "(/v1/organizations/cost_report) require an Anthropic Admin API Key (sk-ant-admin...). "
        "Anthropic does not expose prepaid balance via a public API."
    )

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_connection_test=True,
            supports_usage=True,
            supports_costs=True,
            supports_balance=False,
            supports_pricing=True,
            requires_admin_key_for_usage=True,
            capability_notes=(
                "Usage & Cost reports require an Anthropic Organization Admin key (sk-ant-admin...). "
                "Prepaid credit balance is not exposed via public API."
            ),
        )

    def _headers(self, creds: ConnectorCredentials, *, admin: bool = False) -> dict[str, str]:
        headers = {
            "x-api-key": creds.api_key.strip(),
            "anthropic-version": "2023-06-01",
        }
        # Non-admin endpoints (e.g. /v1/models) scoped to a service account key
        # require the anthropic-workspace-id header.
        if not admin and creds.workspace_id:
            headers["anthropic-workspace-id"] = creds.workspace_id.strip()
        return headers

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        is_admin = creds.api_key.strip().startswith("sk-ant-admin")
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/models",
            headers=self._headers(creds, admin=False),
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            msg = (
                "Connected with Anthropic Admin API Key."
                if is_admin
                else "Connected with Standard Anthropic API Key (Admin key required for org usage/cost reports)."
            )
            return ConnectionTestResult(
                success=True,
                status="connected",
                message=msg,
                is_admin_key=is_admin,
                detected_models_count=len(data),
            )
        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"Anthropic authentication failed (HTTP {resp.status_code}).",
        )

    async def fetch_usage(
        self,
        creds: ConnectorCredentials,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedUsageRecord]:
        params: dict[str, Any] = {
            "starting_at": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ending_at": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bucket_width": "1d",
            "group_by[]": "model",
        }
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/organizations/usage_report/messages",
            headers=self._headers(creds, admin=True),
            params=params,
        )
        records: list[NormalizedUsageRecord] = []
        if resp.status_code in (401, 403, 404):
            return records
        resp.raise_for_status()
        payload = resp.json()
        for bucket in payload.get("data", []):
            start_str = bucket.get("starting_at")
            b_start = (
                datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if start_str
                else start_time
            )
            for item in bucket.get("results", []):
                model_id = item.get("model") or "claude-3-5-sonnet-20241022"
                in_tok = int(item.get("uncached_input_tokens") or item.get("input_tokens") or 0)
                out_tok = int(item.get("output_tokens") or 0)
                cached_tok = int(item.get("cache_read_input_tokens") or 0)
                ext_id = f"anthropic-usage-{b_start.strftime('%Y-%m-%d')}-{model_id}"
                records.append(
                    NormalizedUsageRecord(
                        model_id=model_id,
                        timestamp=b_start,
                        period_start=b_start,
                        period_end=b_start,
                        input_tokens=in_tok,
                        output_tokens=out_tok,
                        cached_input_tokens=cached_tok,
                        total_tokens=in_tok + out_tok + cached_tok,
                        requests_count=1,
                        currency="USD",
                        actual_cost=None,
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
        params: dict[str, Any] = {
            "starting_at": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ending_at": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bucket_width": "1d",
        }
        resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/organizations/cost_report",
            headers=self._headers(creds, admin=True),
            params=params,
        )
        records: list[NormalizedCostRecord] = []
        if resp.status_code in (401, 403, 404):
            return records
        resp.raise_for_status()
        payload = resp.json()
        for idx, bucket in enumerate(payload.get("data", [])):
            start_str = bucket.get("starting_at")
            b_start = (
                datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                if start_str
                else datetime.now(UTC)
            )
            for r_idx, item in enumerate(bucket.get("results", [])):
                amount = float(item.get("amount") or 0.0)
                currency = (item.get("currency") or "USD").upper()
                model_id = item.get("model") or "anthropic-org-cost"
                if amount <= 0:
                    continue
                records.append(
                    NormalizedCostRecord(
                        model_id=model_id,
                        period_start=b_start,
                        period_end=b_start,
                        amount=amount,
                        currency=currency,
                        cost_type="actual",
                        data_source="official_billing_api",
                        external_record_id=f"anthropic-cost-{b_start.strftime('%Y-%m-%d')}-{idx}-{r_idx}",
                    )
                )
        return records

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="Anthropic does not expose prepaid credit balances via an official API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(ANTHROPIC_OFFICIAL_PRICING)
