from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.entities import AIModel, AppSetting, ExchangeRate, ModelPrice, Provider
from connectors.registry import list_connectors

DEFAULT_SETTINGS_MAP = {
    "default_currency": settings.default_currency,
    "demo_mode": "true" if settings.demo_mode else "false",
    "sync_usage_interval_minutes": str(settings.sync_usage_interval_minutes),
    "sync_costs_interval_minutes": str(settings.sync_costs_interval_minutes),
    "sync_balances_interval_minutes": str(settings.sync_balances_interval_minutes),
    "sync_pricing_interval_minutes": str(settings.sync_pricing_interval_minutes),
}


def seed_reference_data(db: Session) -> None:
    """
    Idempotently seeds providers, official model pricing catalog, default settings,
    and reference USD/EUR exchange rates.
    """
    for connector in list_connectors():
        caps = connector.get_capabilities()
        existing = db.get(Provider, connector.provider_id)
        if not existing:
            provider = Provider(
                id=connector.provider_id,
                name=connector.provider_name,
                category_priority=connector.category_priority,
                api_base_url=connector.api_base_url,
                docs_url=connector.docs_url,
                auth_instructions=connector.auth_instructions,
                supports_connection_test=caps.supports_connection_test,
                supports_usage=caps.supports_usage,
                supports_costs=caps.supports_costs,
                supports_balance=caps.supports_balance,
                supports_pricing=caps.supports_pricing,
                requires_admin_key_for_usage=caps.requires_admin_key_for_usage,
                capability_notes=caps.capability_notes,
            )
            db.add(provider)
            db.flush()
        else:
            existing.name = connector.provider_name
            existing.category_priority = connector.category_priority
            existing.api_base_url = connector.api_base_url
            existing.docs_url = connector.docs_url
            existing.auth_instructions = connector.auth_instructions
            existing.supports_connection_test = caps.supports_connection_test
            existing.supports_usage = caps.supports_usage
            existing.supports_costs = caps.supports_costs
            existing.supports_balance = caps.supports_balance
            existing.supports_pricing = caps.supports_pricing
            existing.requires_admin_key_for_usage = caps.requires_admin_key_for_usage
            existing.capability_notes = caps.capability_notes

    # Seed default settings
    for key, val in DEFAULT_SETTINGS_MAP.items():
        if not db.get(AppSetting, key):
            db.add(AppSetting(key=key, value=val))

    # Seed reference exchange rates (USD <-> EUR)
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    has_fx = db.scalar(select(ExchangeRate).limit(1))
    if not has_fx:
        db.add_all(
            [
                ExchangeRate(
                    base_currency="USD",
                    target_currency="EUR",
                    rate=0.92,
                    effective_date=today_str,
                    source="ecb_reference",
                ),
                ExchangeRate(
                    base_currency="EUR",
                    target_currency="USD",
                    rate=round(1.0 / 0.92, 6),
                    effective_date=today_str,
                    source="ecb_reference",
                ),
            ]
        )

    db.commit()


async def seed_initial_pricing(db: Session) -> None:
    """Populates initial official model pricing if the table is empty."""
    has_prices = db.scalar(select(ModelPrice).limit(1))
    if has_prices:
        return

    for connector in list_connectors():
        prices = await connector.fetch_model_pricing(None)
        for p in prices:
            upsert_model_price(db, connector.provider_id, p)
    db.commit()


def upsert_model_price(db: Session, provider_id: str, price_dto) -> None:
    """
    Preserves historical model pricing: if a price changes, marks previous record is_current=False
    and inserts a new ModelPrice record.
    """
    ai_model = db.scalar(
        select(AIModel).where(
            AIModel.provider_id == provider_id,
            AIModel.model_id == price_dto.model_id,
        )
    )
    if not ai_model:
        ai_model = AIModel(
            provider_id=provider_id,
            model_id=price_dto.model_id,
            display_name=price_dto.display_name,
            context_window=price_dto.context_window,
            is_active=True,
        )
        db.add(ai_model)
        db.flush()

    current_price = db.scalar(
        select(ModelPrice).where(
            ModelPrice.model_ref_id == ai_model.id,
            ModelPrice.is_current.is_(True),
        )
    )
    if current_price:
        same_in = abs(current_price.input_price_per_million - price_dto.input_price_per_million) < 1e-7
        same_out = abs(current_price.output_price_per_million - price_dto.output_price_per_million) < 1e-7
        same_cache = current_price.cached_input_price_per_million == price_dto.cached_input_price_per_million
        if same_in and same_out and same_cache:
            return
        current_price.is_current = False

    new_price = ModelPrice(
        model_ref_id=ai_model.id,
        provider_id=provider_id,
        model_id=price_dto.model_id,
        input_price_per_million=price_dto.input_price_per_million,
        output_price_per_million=price_dto.output_price_per_million,
        cached_input_price_per_million=price_dto.cached_input_price_per_million,
        currency=price_dto.currency,
        price_source=price_dto.price_source,
        is_current=True,
    )
    db.add(new_price)
