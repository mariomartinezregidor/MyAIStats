from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category_priority: Mapped[int] = mapped_column(Integer, default=1)
    api_base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    docs_url: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_instructions: Mapped[str] = mapped_column(Text, nullable=False)

    # Explicit capability flags based on official API availability
    supports_connection_test: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_usage: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_costs: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_balance: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_pricing: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_admin_key_for_usage: Mapped[bool] = mapped_column(Boolean, default=False)
    capability_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="provider", cascade="all, delete-orphan"
    )
    models: Mapped[list["AIModel"]] = relationship(
        "AIModel", back_populates="provider", cascade="all, delete-orphan"
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    external_org_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="unverified")  # connected, error, unverified
    status_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_admin_key: Mapped[bool] = mapped_column(Boolean, default=False)
    low_balance_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    provider: Mapped["Provider"] = relationship("Provider", back_populates="accounts")
    credential: Mapped["Credential | None"] = relationship(
        "Credential", back_populates="account", uselist=False, cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="account", cascade="all, delete-orphan"
    )
    cost_records: Mapped[list["CostRecord"]] = relationship(
        "CostRecord", back_populates="account", cascade="all, delete-orphan"
    )
    balance_snapshots: Mapped[list["BalanceSnapshot"]] = relationship(
        "BalanceSnapshot", back_populates="account", cascade="all, delete-orphan"
    )
    sync_jobs: Mapped[list["SyncJob"]] = relationship(
        "SyncJob", back_populates="account", cascade="all, delete-orphan"
    )


class Credential(Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_extra_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    masked_hint: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), default="fernet_local")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    account: Mapped["Account"] = relationship("Account", back_populates="credential")


class AIModel(Base):
    __tablename__ = "models"
    __table_args__ = (UniqueConstraint("provider_id", "model_id", name="uq_provider_model"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    provider: Mapped["Provider"] = relationship("Provider", back_populates="models")
    prices: Mapped[list["ModelPrice"]] = relationship(
        "ModelPrice", back_populates="model", cascade="all, delete-orphan"
    )


class ModelPrice(Base):
    """
    Keeps historical model pricing rather than overwriting previous prices.
    """

    __tablename__ = "model_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_ref_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    input_price_per_million: Mapped[float] = mapped_column(Float, nullable=False)
    output_price_per_million: Mapped[float] = mapped_column(Float, nullable=False)
    cached_input_price_per_million: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    price_source: Mapped[str] = mapped_column(
        String(64), default="official_api", nullable=False
    )  # official_api, official_catalog
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    model: Mapped["AIModel"] = relationship("AIModel", back_populates="prices")


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("account_id", "external_record_id", name="uq_usage_account_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached_input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requests_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    # Kept strictly separate: actual_cost is reported by provider; estimated_cost is computed from ModelPrice
    actual_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_type: Mapped[str] = mapped_column(
        String(32), default="estimated", nullable=False
    )  # actual, estimated, none
    data_source: Mapped[str] = mapped_column(
        String(64), default="official_api", nullable=False
    )  # official_api, demo
    data_precision: Mapped[str] = mapped_column(
        String(32), default="exact", nullable=False
    )  # exact, bucket_1d, bucket_1h, estimated
    external_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped["Account"] = relationship("Account", back_populates="usage_records")


class CostRecord(Base):
    """
    Stores official billing/cost line items or daily cost buckets returned by providers.
    Explicitly separates 'actual' (official billing API) vs 'estimated' (calculated from usage * model price).
    """

    __tablename__ = "cost_records"
    __table_args__ = (
        UniqueConstraint("account_id", "external_record_id", name="uq_cost_account_external_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    cost_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # "actual" | "estimated"
    data_source: Mapped[str] = mapped_column(
        String(64), default="official_billing_api", nullable=False
    )
    external_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    account: Mapped["Account"] = relationship("Account", back_populates="cost_records")


class BalanceSnapshot(Base):
    """
    Stores confirmed available balances or credits where officially supported.
    Never stores guessed balances.
    """

    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    available_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_credits: Mapped[float | None] = mapped_column(Float, nullable=True)
    used_credits: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    is_supported: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_source: Mapped[str] = mapped_column(String(64), default="official_api", nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    account: Mapped["Account"] = relationship("Account", back_populates="balance_snapshots")


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(
        String(64), default="full", nullable=False
    )  # full, usage, costs, balances, pricing
    status: Mapped[str] = mapped_column(
        String(32), default="running", nullable=False, index=True
    )  # running, completed, partial, failed
    records_synced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    account: Mapped["Account | None"] = relationship("Account", back_populates="sync_jobs")
    errors: Mapped[list["SyncError"]] = relationship(
        "SyncError", back_populates="sync_job", cascade="all, delete-orphan"
    )


class SyncError(Base):
    __tablename__ = "sync_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sync_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[str] = mapped_column(String(64), nullable=False)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capability: Mapped[str] = mapped_column(String(64), nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    sync_job: Mapped["SyncJob"] = relationship("SyncJob", back_populates="errors")


class AppSetting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("base_currency", "target_currency", "effective_date", name="uq_fx_pair_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    target_currency: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    effective_date: Mapped[str] = mapped_column(String(16), nullable=False)  # YYYY-MM-DD
    source: Mapped[str] = mapped_column(String(64), default="ecb_reference", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
