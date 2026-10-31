from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.models.entities import AppSetting, ExchangeRate, ModelPrice


def get_app_setting(db: Session, key: str, default: str = "") -> str:
    row = db.get(AppSetting, key)
    return row.value if row else default


def is_demo_mode_enabled(db: Session) -> bool:
    val = get_app_setting(db, "demo_mode", "true").lower()
    return val in ("true", "1", "yes")


def get_default_currency(db: Session) -> str:
    cur = get_app_setting(db, "default_currency", "USD").upper()
    return cur if cur in ("USD", "EUR") else "USD"


def get_exchange_rate(
    db: Session, from_currency: str, to_currency: str
) -> tuple[float, str, str]:
    """
    Returns (rate, effective_date, source) from stored ExchangeRate records.
    Never silently overwrites original values.
    """
    src = (from_currency or "USD").upper()
    dst = (to_currency or "USD").upper()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    if src == dst:
        return 1.0, today_str, "identity"

    row = db.scalar(
        select(ExchangeRate)
        .where(
            ExchangeRate.base_currency == src,
            ExchangeRate.target_currency == dst,
        )
        .order_by(desc(ExchangeRate.effective_date), desc(ExchangeRate.id))
        .limit(1)
    )
    if row:
        return row.rate, row.effective_date, row.source

    # Fallback inverse lookup
    inverse = db.scalar(
        select(ExchangeRate)
        .where(
            ExchangeRate.base_currency == dst,
            ExchangeRate.target_currency == src,
        )
        .order_by(desc(ExchangeRate.effective_date), desc(ExchangeRate.id))
        .limit(1)
    )
    if inverse and inverse.rate > 0:
        return round(1.0 / inverse.rate, 6), inverse.effective_date, f"{inverse.source}_inverse"

    return 1.0, today_str, "unavailable_rate_1_to_1"


def convert_amount(
    db: Session, amount: float | None, from_currency: str, to_currency: str
) -> tuple[float | None, float, str]:
    if amount is None:
        rate, eff_date, _ = get_exchange_rate(db, from_currency, to_currency)
        return None, rate, eff_date
    rate, eff_date, _ = get_exchange_rate(db, from_currency, to_currency)
    return round(amount * rate, 6), rate, eff_date


def estimate_cost_from_pricing(
    db: Session,
    provider_id: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> tuple[float | None, str]:
    """
    Calculates estimated cost strictly when actual cost is unavailable and official model pricing is known.
    Returns (estimated_amount, currency) or (None, "USD").
    """
    price = db.scalar(
        select(ModelPrice)
        .where(
            ModelPrice.provider_id == provider_id,
            ModelPrice.model_id == model_id,
            ModelPrice.is_current.is_(True),
        )
        .limit(1)
    )
    if not price:
        # Try prefix match (e.g., gpt-4o-2024-08-06 -> gpt-4o)
        candidates = db.scalars(
            select(ModelPrice).where(
                ModelPrice.provider_id == provider_id,
                ModelPrice.is_current.is_(True),
            )
        ).all()
        for cand in candidates:
            if model_id.startswith(cand.model_id):
                price = cand
                break

    if not price:
        return None, "USD"

    uncached_in = max(0, input_tokens - cached_input_tokens)
    in_cost = (uncached_in / 1_000_000.0) * price.input_price_per_million
    out_cost = (output_tokens / 1_000_000.0) * price.output_price_per_million
    cache_rate = (
        price.cached_input_price_per_million
        if price.cached_input_price_per_million is not None
        else price.input_price_per_million
    )
    cache_cost = (cached_input_tokens / 1_000_000.0) * cache_rate
    return round(in_cost + out_cost + cache_cost, 6), price.currency
