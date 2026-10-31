import respx
from fastapi.testclient import TestClient
from httpx import Response

from backend.app.core.security import CredentialVault
from backend.app.main import app


def test_credential_vault_encryption_and_masking():
    vault = CredentialVault()
    secret = "sk-proj-super-secret-api-key-9876"
    ciphertext = vault.encrypt(secret)
    assert ciphertext != secret
    assert "super-secret" not in ciphertext
    assert vault.decrypt(ciphertext) == secret
    assert vault.mask_key(secret) == "sk-pro...9876"


def test_providers_and_demo_dashboard():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        providers_resp = client.get("/api/providers")
        assert providers_resp.status_code == 200
        providers = providers_resp.json()
        assert len(providers) == 12
        by_id = {p["id"]: p for p in providers}
        assert by_id["openai"]["supports_balance"] is False
        assert by_id["openai"]["requires_admin_key_for_usage"] is True
        assert by_id["openrouter"]["supports_balance"] is True
        assert by_id["deepseek"]["supports_balance"] is True
        assert by_id["google"]["supports_balance"] is False

        summary_resp = client.get("/api/dashboard/summary?preset=30d&currency=USD")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert summary["demo_mode_active"] is True
        assert summary["actual_billed_cost"] > 0
        assert summary["estimated_cost"] > 0
        assert abs(
            summary["total_combined_spending"]
            - (summary["actual_billed_cost"] + summary["estimated_cost"])
        ) < 0.01
        assert summary["confirmed_available_balance"] > 0
        assert summary["input_tokens"] > 0
        assert summary["output_tokens"] > 0

        # Test currency conversion to EUR
        summary_eur = client.get("/api/dashboard/summary?preset=30d&currency=EUR").json()
        assert summary_eur["display_currency"] == "EUR"
        assert summary_eur["total_combined_spending"] < summary["total_combined_spending"]


@respx.mock
def test_account_connect_sync_and_no_key_leak():
    respx.get("https://openrouter.ai/api/v1/auth/key").mock(
        return_value=Response(
            200,
            json={"data": {"label": "test-key", "usage": 12.5, "limit": 100.0, "limit_remaining": 87.5}},
        )
    )
    respx.get("https://openrouter.ai/api/v1/credits").mock(
        return_value=Response(
            200,
            json={"data": {"total_credits": 100.0, "total_usage": 12.5}},
        )
    )
    respx.get("https://openrouter.ai/api/v1/activity").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "date": "2026-10-30T10:00:00Z",
                        "model": "openai/gpt-4o",
                        "prompt_tokens": 12000,
                        "completion_tokens": 4000,
                        "cached_tokens": 2000,
                        "requests": 5,
                        "usage": 0.065,
                    }
                ]
            },
        )
    )
    respx.get("https://openrouter.ai/api/v1/models").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "openai/gpt-4o",
                        "name": "OpenRouter: GPT-4o",
                        "context_length": 128000,
                        "pricing": {"prompt": "0.0000025", "completion": "0.00001"},
                    }
                ]
            },
        )
    )

    with TestClient(app) as client:
        raw_key = "sk-or-v1-secret-test-credential-1234"
        connect_resp = client.post(
            "/api/accounts/connect",
            json={
                "provider_id": "openrouter",
                "name": "Test OpenRouter Account",
                "api_key": raw_key,
                "low_balance_threshold": 20.0,
            },
        )
        assert connect_resp.status_code == 201
        acc = connect_resp.json()
        acc_id = acc["id"]
        assert raw_key not in connect_resp.text
        assert acc["masked_key_hint"] == "sk-or-...1234"
        assert acc["status"] == "connected"

        # Test manual sync
        sync_resp = client.post(f"/api/accounts/{acc_id}/sync")
        assert sync_resp.status_code == 200
        job = sync_resp.json()
        assert job["status"] == "completed"
        assert job["records_synced"] >= 2

        # Verify balances endpoint includes confirmed 87.50 balance
        balances = client.get("/api/balances").json()
        matching = [b for b in balances if b["account_id"] == acc_id]
        assert len(matching) == 1
        assert matching[0]["available_balance"] == 87.5
        assert matching[0]["is_supported"] is True

        # Verify CSV & JSON exports
        csv_resp = client.get("/api/export/csv?dataset=usage")
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers["content-type"]

        json_resp = client.get("/api/export/json?dataset=balances")
        assert json_resp.status_code == 200
        assert "application/json" in json_resp.headers["content-type"]

        # Clean up test account
        del_resp = client.delete(f"/api/accounts/{acc_id}")
        assert del_resp.status_code == 204
