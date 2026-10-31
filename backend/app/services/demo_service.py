from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.schemas.api_schemas import (
    AccountOut,
    BalanceItemOut,
    CostItemOut,
    UsageItemOut,
)
from backend.app.services.finance_service import convert_amount


def get_demo_accounts() -> list[AccountOut]:
    now = datetime.now(UTC)
    return [
        AccountOut(
            id=-101,
            provider_id="openai",
            provider_name="OpenAI",
            name="[DEMO] OpenAI Production Org",
            external_org_id="org-demo-prod",
            status="connected",
            status_message="Demo Mode: Organization Admin Key simulated",
            is_admin_key=True,
            masked_key_hint="sk-adm...demo",
            low_balance_threshold=None,
            last_sync_at=now - timedelta(minutes=8),
            created_at=now - timedelta(days=30),
            is_demo=True,
        ),
        AccountOut(
            id=-102,
            provider_id="openrouter",
            provider_name="OpenRouter",
            name="[DEMO] OpenRouter Multi-Model Router",
            external_org_id=None,
            status="connected",
            status_message="Demo Mode: Credits & Activity simulated",
            is_admin_key=True,
            masked_key_hint="sk-or-...demo",
            low_balance_threshold=15.0,
            last_sync_at=now - timedelta(minutes=5),
            created_at=now - timedelta(days=25),
            is_demo=True,
        ),
        AccountOut(
            id=-103,
            provider_id="anthropic",
            provider_name="Anthropic",
            name="[DEMO] Anthropic R&D Workspace",
            external_org_id="wrk-demo-01",
            status="connected",
            status_message="Demo Mode: Usage & Cost reports simulated",
            is_admin_key=True,
            masked_key_hint="sk-ant...demo",
            low_balance_threshold=None,
            last_sync_at=now - timedelta(minutes=12),
            created_at=now - timedelta(days=20),
            is_demo=True,
        ),
        AccountOut(
            id=-104,
            provider_id="deepseek",
            provider_name="DeepSeek",
            name="[DEMO] DeepSeek Reasoning API",
            external_org_id=None,
            status="connected",
            status_message="Demo Mode: Confirmed Balance simulated",
            is_admin_key=False,
            masked_key_hint="ds-key...demo",
            low_balance_threshold=10.0,
            last_sync_at=now - timedelta(minutes=14),
            created_at=now - timedelta(days=15),
            is_demo=True,
        ),
    ]


def get_demo_balances(db: Session, display_currency: str) -> list[BalanceItemOut]:
    now = datetime.now(UTC)
    or_conv, _, _ = convert_amount(db, 64.40, "USD", display_currency)
    ds_conv, _, _ = convert_amount(db, 18.75, "USD", display_currency)
    return [
        BalanceItemOut(
            account_id=-102,
            account_name="[DEMO] OpenRouter Multi-Model Router",
            provider_id="openrouter",
            provider_name="OpenRouter",
            is_supported=True,
            available_balance=64.40,
            total_credits=120.00,
            used_credits=55.60,
            original_currency="USD",
            converted_available_balance=or_conv,
            display_currency=display_currency,
            low_balance_threshold=15.0,
            is_low_balance=False,
            status_note="[DEMO] Confirmed via OpenRouter /api/v1/credits",
            captured_at=now - timedelta(minutes=5),
            is_demo=True,
        ),
        BalanceItemOut(
            account_id=-104,
            account_name="[DEMO] DeepSeek Reasoning API",
            provider_id="deepseek",
            provider_name="DeepSeek",
            is_supported=True,
            available_balance=18.75,
            total_credits=50.00,
            used_credits=31.25,
            original_currency="USD",
            converted_available_balance=ds_conv,
            display_currency=display_currency,
            low_balance_threshold=20.0,
            is_low_balance=True,
            status_note="[DEMO] Confirmed via DeepSeek /user/balance",
            captured_at=now - timedelta(minutes=14),
            is_demo=True,
        ),
        BalanceItemOut(
            account_id=-101,
            account_name="[DEMO] OpenAI Production Org",
            provider_id="openai",
            provider_name="OpenAI",
            is_supported=False,
            available_balance=None,
            total_credits=None,
            used_credits=None,
            original_currency="USD",
            converted_available_balance=None,
            display_currency=display_currency,
            low_balance_threshold=None,
            is_low_balance=False,
            status_note="Unsupported by official OpenAI public API (Costs & Usage are supported).",
            captured_at=now - timedelta(minutes=8),
            is_demo=True,
        ),
        BalanceItemOut(
            account_id=-103,
            account_name="[DEMO] Anthropic R&D Workspace",
            provider_id="anthropic",
            provider_name="Anthropic",
            is_supported=False,
            available_balance=None,
            total_credits=None,
            used_credits=None,
            original_currency="USD",
            converted_available_balance=None,
            display_currency=display_currency,
            low_balance_threshold=None,
            is_low_balance=False,
            status_note="Unsupported by official Anthropic API (Usage & Cost reports are supported).",
            captured_at=now - timedelta(minutes=12),
            is_demo=True,
        ),
    ]


def generate_demo_usage_and_costs(
    db: Session,
    display_currency: str,
    start_dt: datetime,
    end_dt: datetime,
) -> tuple[list[UsageItemOut], list[CostItemOut]]:
    now = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
    usage_items: list[UsageItemOut] = []
    cost_items: list[CostItemOut] = []

    demo_specs = [
        (
            "openai",
            "OpenAI",
            -101,
            "[DEMO] OpenAI Production Org",
            "gpt-4o",
            420_000,
            145_000,
            160_000,
            True,  # actual cost available
            2.30,
        ),
        (
            "openai",
            "OpenAI",
            -101,
            "[DEMO] OpenAI Production Org",
            "o3-mini",
            280_000,
            95_000,
            80_000,
            False,  # estimated cost from pricing
            0.68,
        ),
        (
            "openrouter",
            "OpenRouter",
            -102,
            "[DEMO] OpenRouter Multi-Model Router",
            "anthropic/claude-3.5-sonnet",
            310_000,
            110_000,
            90_000,
            True,
            2.34,
        ),
        (
            "anthropic",
            "Anthropic",
            -103,
            "[DEMO] Anthropic R&D Workspace",
            "claude-3-7-sonnet-20250219",
            360_000,
            125_000,
            130_000,
            True,
            2.61,
        ),
        (
            "deepseek",
            "DeepSeek",
            -104,
            "[DEMO] DeepSeek Reasoning API",
            "deepseek-reasoner",
            510_000,
            210_000,
            220_000,
            False,
            0.65,
        ),
    ]

    record_id = -1000
    for day_offset in range(30, -1, -1):
        day_dt = now - timedelta(days=day_offset)
        if day_dt < start_dt or day_dt > end_dt:
            continue

        wave = 0.75 + ((30 - day_offset) % 7) * 0.08
        for (
            prov_id,
            prov_name,
            acc_id,
            acc_name,
            model_id,
            base_in,
            base_out,
            base_cache,
            is_actual,
            base_cost,
        ) in demo_specs:
            record_id -= 1
            in_tok = int(base_in * wave)
            out_tok = int(base_out * wave)
            cache_tok = int(base_cache * wave)
            raw_cost = round(base_cost * wave, 4)
            conv_cost, fx_rate, fx_date = convert_amount(db, raw_cost, "USD", display_currency)

            usage_items.append(
                UsageItemOut(
                    id=record_id,
                    provider_id=prov_id,
                    provider_name=prov_name,
                    account_id=acc_id,
                    account_name=acc_name,
                    model_id=model_id,
                    timestamp=day_dt,
                    period_start=day_dt,
                    period_end=day_dt,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cached_input_tokens=cache_tok,
                    total_tokens=in_tok + out_tok,
                    requests_count=max(12, int(48 * wave)),
                    original_currency="USD",
                    actual_cost=raw_cost if is_actual else None,
                    estimated_cost=None if is_actual else raw_cost,
                    converted_actual_cost=conv_cost if is_actual else None,
                    converted_estimated_cost=None if is_actual else conv_cost,
                    display_currency=display_currency,
                    cost_type="actual" if is_actual else "estimated",
                    data_source="demo",
                    data_precision="bucket_1d",
                    is_demo=True,
                )
            )
            cost_items.append(
                CostItemOut(
                    id=record_id,
                    provider_id=prov_id,
                    provider_name=prov_name,
                    account_id=acc_id,
                    account_name=acc_name,
                    model_id=model_id,
                    period_start=day_dt,
                    period_end=day_dt,
                    amount=raw_cost,
                    original_currency="USD",
                    converted_amount=conv_cost or raw_cost,
                    display_currency=display_currency,
                    exchange_rate_used=fx_rate,
                    exchange_rate_date=fx_date,
                    cost_type="actual" if is_actual else "estimated",
                    data_source="demo",
                    is_demo=True,
                )
            )

    usage_items.sort(key=lambda x: x.timestamp, reverse=True)
    cost_items.sort(key=lambda x: x.period_start, reverse=True)
    return usage_items, cost_items
