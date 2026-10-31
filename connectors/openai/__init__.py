"""OpenAI Official Connector."""

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

OPENAI_OFFICIAL_PRICING: list[NormalizedModelPrice] = [
    NormalizedModelPrice(
        model_id="gpt-4o",
        display_name="GPT-4o",
        context_window=128000,
        input_price_per_million=2.50,
        output_price_per_million=10.00,
        cached_input_price_per_million=1.25,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="gpt-4o-mini",
        display_name="GPT-4o mini",
        context_window=128000,
        input_price_per_million=0.15,
        output_price_per_million=0.60,
        cached_input_price_per_million=0.075,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="o3-mini",
        display_name="OpenAI o3-mini",
        context_window=200000,
        input_price_per_million=1.10,
        output_price_per_million=4.40,
        cached_input_price_per_million=0.55,
        currency="USD",
        price_source="official_catalog",
    ),
    NormalizedModelPrice(
        model_id="o1",
        display_name="OpenAI o1",
        context_window=200000,
        input_price_per_million=15.00,
        output_price_per_million=60.00,
        cached_input_price_per_million=7.50,
        currency="USD",
        price_source="official_catalog",
    ),
]


class OpenAIConnector(BaseConnector):
    provider_id = "openai"
    provider_name = "OpenAI"
    category_priority = 1
    api_base_url = "https://api.openai.com"
    docs_url = "https://platform.openai.com/docs/api-reference/usage"
    auth_instructions = (
        "Standard Project API keys (sk-proj-...) can test connectivity and list models. "
        "To retrieve organization-wide token usage (/v1/organization/usage/completions) and "
        "actual billed costs (/v1/organization/costs), OpenAI requires an Organization Admin API Key "
        "(sk-admin-...). OpenAI does not expose prepaid credit balance via a public REST API."
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
                "Usage and Costs endpoints require an OpenAI Organization Admin API key (sk-admin-...). "
                "Prepaid credit balance is not exposed via public API."
            ),
        )

    def _headers(self, creds: ConnectorCredentials) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {creds.api_key.strip()}"}
        if creds.organization_id:
            headers["OpenAI-Organization"] = creds.organization_id.strip()
        return headers

    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        now_ts = int(datetime.now(UTC).timestamp())
        start_ts = now_ts - 86400
        # Check if key has Admin organization usage permissions
        usage_resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/organization/usage/completions",
            headers=self._headers(creds),
            params={"start_time": start_ts, "limit": 1},
        )
        if usage_resp.status_code == 200:
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected with OpenAI Organization Admin privileges (Usage & Costs active).",
                is_admin_key=True,
            )

        # Fallback to standard /v1/models check for project keys
        models_resp = await self.http.request(
            "GET",
            f"{self.api_base_url}/v1/models",
            headers=self._headers(creds),
        )
        if models_resp.status_code == 200:
            payload = models_resp.json()
            models_list = payload.get("data", []) if isinstance(payload, dict) else []
            return ConnectionTestResult(
                success=True,
                status="connected",
                message="Connected with Standard API Key. Note: Organization Usage & Costs require an Admin Key (sk-admin-...).",
                is_admin_key=False,
                detected_models_count=len(models_list),
                warnings=[
                    "This key is a standard project key. Provide an OpenAI Admin API key (sk-admin-...) to sync organization usage and costs."
                ],
            )

        return ConnectionTestResult(
            success=False,
            status="error",
            message=f"OpenAI authentication failed (HTTP {models_resp.status_code}). Verify your API key.",
        )

    async def fetch_usage(
        self,
        creds: ConnectorCredentials,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedUsageRecord]:
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        records: list[NormalizedUsageRecord] = []
        next_page: str | None = None

        for _ in range(25):  # safe pagination cap
            params: dict[str, Any] = {
                "start_time": start_ts,
                "end_time": end_ts,
                "bucket_width": "1d",
                "group_by": ["model"],
                "limit": 31,
            }
            if next_page:
                params["page"] = next_page

            resp = await self.http.request(
                "GET",
                f"{self.api_base_url}/v1/organization/usage/completions",
                headers=self._headers(creds),
                params=params,
            )
            if resp.status_code in (401, 403):
                # Standard non-admin key cannot read organization usage
                return records
            resp.raise_for_status()
            payload = resp.json()
            for bucket in payload.get("data", []):
                b_start = datetime.fromtimestamp(
                    bucket.get("start_time", start_ts), tz=UTC
                )
                b_end = datetime.fromtimestamp(
                    bucket.get("end_time", end_ts), tz=UTC
                )
                for result in bucket.get("results", []):
                    model_id = result.get("model") or "openai-unspecified"
                    in_tok = int(result.get("input_tokens") or 0)
                    out_tok = int(result.get("output_tokens") or 0)
                    cached_tok = int(result.get("input_cached_tokens") or 0)
                    reqs = int(result.get("num_model_requests") or 1)
                    if in_tok == 0 and out_tok == 0:
                        continue
                    ext_id = f"openai-usage-{int(b_start.timestamp())}-{model_id}"
                    records.append(
                        NormalizedUsageRecord(
                            model_id=model_id,
                            timestamp=b_start,
                            period_start=b_start,
                            period_end=b_end,
                            input_tokens=in_tok,
                            output_tokens=out_tok,
                            cached_input_tokens=cached_tok,
                            total_tokens=in_tok + out_tok,
                            requests_count=reqs,
                            currency="USD",
                            actual_cost=None,
                            data_source="official_api",
                            data_precision="bucket_1d",
                            external_record_id=ext_id,
                        )
                    )
            if payload.get("has_more") and payload.get("next_page"):
                next_page = payload["next_page"]
            else:
                break
        return records

    async def fetch_costs(
        self,
        creds: ConnectorCredentials,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedCostRecord]:
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        records: list[NormalizedCostRecord] = []
        next_page: str | None = None

        for _ in range(25):
            params: dict[str, Any] = {
                "start_time": start_ts,
                "end_time": end_ts,
                "bucket_width": "1d",
                "limit": 31,
            }
            if next_page:
                params["page"] = next_page

            resp = await self.http.request(
                "GET",
                f"{self.api_base_url}/v1/organization/costs",
                headers=self._headers(creds),
                params=params,
            )
            if resp.status_code in (401, 403):
                return records
            resp.raise_for_status()
            payload = resp.json()
            for bucket in payload.get("data", []):
                b_start = datetime.fromtimestamp(
                    bucket.get("start_time", start_ts), tz=UTC
                )
                b_end = datetime.fromtimestamp(
                    bucket.get("end_time", end_ts), tz=UTC
                )
                for idx, result in enumerate(bucket.get("results", [])):
                    amount_obj = result.get("amount") or {}
                    val = float(amount_obj.get("value") or 0.0)
                    currency = (amount_obj.get("currency") or "usd").upper()
                    line_item = result.get("line_item") or "openai-organization-cost"
                    if val <= 0:
                        continue
                    ext_id = f"openai-cost-{int(b_start.timestamp())}-{line_item}-{idx}"
                    records.append(
                        NormalizedCostRecord(
                            model_id=line_item,
                            period_start=b_start,
                            period_end=b_end,
                            amount=val,
                            currency=currency,
                            cost_type="actual",
                            data_source="official_billing_api",
                            external_record_id=ext_id,
                        )
                    )
            if payload.get("has_more") and payload.get("next_page"):
                next_page = payload["next_page"]
            else:
                break
        return records

    async def fetch_balance(self, creds: ConnectorCredentials) -> NormalizedBalanceSnapshot:
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=False,
            status_note="OpenAI does not expose prepaid credit balances via an official public API.",
            data_source="unsupported",
        )

    async def fetch_model_pricing(
        self, creds: ConnectorCredentials | None = None
    ) -> list[NormalizedModelPrice]:
        return list(OPENAI_OFFICIAL_PRICING)
