from datetime import UTC, datetime, timedelta

import pytest
import respx
from httpx import Response

from connectors.anthropic import AnthropicConnector
from connectors.base.http_client import SSRFProtectionError, validate_outbound_url
from connectors.base.types import ConnectorCredentials
from connectors.deepseek import DeepSeekConnector
from connectors.google import GoogleGeminiConnector
from connectors.openai import OpenAIConnector
from connectors.openrouter import OpenRouterConnector


def test_ssrf_protection_blocks_unapproved_hosts_and_http():
    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("http://api.openai.com/v1/models")

    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("https://169.254.169.254/latest/meta-data/")

    with pytest.raises(SSRFProtectionError):
        validate_outbound_url("https://evil.example.com/v1/models")

    # Official hosts over HTTPS pass
    validate_outbound_url("https://api.openai.com/v1/models")
    validate_outbound_url("https://openrouter.ai/api/v1/credits")


@respx.mock
@pytest.mark.asyncio
async def test_openai_connector_standard_vs_admin_and_usage():
    conn = OpenAIConnector()
    creds = ConnectorCredentials(api_key="sk-proj-standard-key-0000")

    # Simulate standard key: 403 on organization usage, 200 on /v1/models
    respx.get("https://api.openai.com/v1/organization/usage/completions").mock(
        return_value=Response(403, json={"error": {"message": "Admin key required"}})
    )
    respx.get("https://api.openai.com/v1/models").mock(
        return_value=Response(200, json={"data": [{"id": "gpt-4o"}, {"id": "o3-mini"}]})
    )

    res = await conn.test_connection(creds)
    assert res.success is True
    assert res.is_admin_key is False
    assert res.detected_models_count == 2
    assert len(res.warnings) == 1

    # Balance is explicitly unsupported on OpenAI
    bal = await conn.fetch_balance(creds)
    assert bal.is_supported is False
    assert bal.available_balance is None


@respx.mock
@pytest.mark.asyncio
async def test_openai_admin_usage_and_costs_normalization():
    conn = OpenAIConnector()
    creds = ConnectorCredentials(api_key="sk-admin-org-key-9999")
    now = datetime.now(UTC)
    start_ts = int((now - timedelta(days=2)).timestamp())
    end_ts = int(now.timestamp())

    respx.get("https://api.openai.com/v1/organization/usage/completions").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "start_time": start_ts,
                        "end_time": end_ts,
                        "results": [
                            {
                                "model": "gpt-4o",
                                "input_tokens": 50000,
                                "output_tokens": 12000,
                                "input_cached_tokens": 10000,
                                "num_model_requests": 14,
                            }
                        ],
                    }
                ],
                "has_more": False,
            },
        )
    )
    respx.get("https://api.openai.com/v1/organization/costs").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "start_time": start_ts,
                        "end_time": end_ts,
                        "results": [
                            {
                                "amount": {"value": 1.42, "currency": "usd"},
                                "line_item": "gpt-4o",
                            }
                        ],
                    }
                ],
                "has_more": False,
            },
        )
    )

    usage = await conn.fetch_usage(creds, now - timedelta(days=2), now)
    assert len(usage) == 1
    assert usage[0].model_id == "gpt-4o"
    assert usage[0].input_tokens == 50000
    assert usage[0].cached_input_tokens == 10000

    costs = await conn.fetch_costs(creds, now - timedelta(days=2), now)
    assert len(costs) == 1
    assert costs[0].amount == 1.42
    assert costs[0].cost_type == "actual"


@respx.mock
@pytest.mark.asyncio
async def test_deepseek_confirmed_balance_and_gemini_capabilities():
    ds = DeepSeekConnector()
    creds = ConnectorCredentials(api_key="ds-live-key-1111")

    respx.get("https://api.deepseek.com/user/balance").mock(
        return_value=Response(
            200,
            json={
                "is_available": True,
                "balance_infos": [
                    {
                        "currency": "USD",
                        "total_balance": "42.80",
                        "granted_balance": "2.80",
                        "topped_up_balance": "40.00",
                    }
                ],
            },
        )
    )
    bal = await ds.fetch_balance(creds)
    assert bal.is_supported is True
    assert bal.available_balance == 42.80
    assert bal.currency == "USD"

    gemini = GoogleGeminiConnector()
    g_caps = gemini.get_capabilities()
    assert g_caps.supports_connection_test is True
    assert g_caps.supports_balance is False
    assert g_caps.supports_usage is False

    anthropic = AnthropicConnector()
    a_caps = anthropic.get_capabilities()
    assert a_caps.supports_usage is True
    assert a_caps.supports_costs is True
    assert a_caps.supports_balance is False

    openrouter = OpenRouterConnector()
    or_caps = openrouter.get_capabilities()
    assert or_caps.supports_balance is True
    assert or_caps.supports_usage is True
    assert or_caps.supports_pricing is True
