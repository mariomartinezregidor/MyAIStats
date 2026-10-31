from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProviderOut(BaseModel):
    id: str
    name: str
    category_priority: int
    api_base_url: str
    docs_url: str
    billing_url: str | None = None
    top_up_url: str | None = None
    recharge_url: str | None = None
    payment_url: str | None = None
    auth_instructions: str
    supports_connection_test: bool
    supports_usage: bool
    supports_costs: bool
    supports_balance: bool
    supports_pricing: bool
    requires_admin_key_for_usage: bool
    capability_notes: str
    connected_accounts_count: int = 0


class AccountConnectRequest(BaseModel):
    provider_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=120)
    api_key: str = Field(..., min_length=4, max_length=512)
    extra_secret: str | None = Field(default=None, max_length=512)
    organization_id: str | None = Field(default=None, max_length=120)
    workspace_id: str | None = Field(default=None, max_length=120)
    low_balance_threshold: float | None = Field(default=None, ge=0.0)


class CredentialRotateRequest(BaseModel):
    api_key: str = Field(..., min_length=4, max_length=512)
    extra_secret: str | None = Field(default=None, max_length=512)
    organization_id: str | None = Field(default=None, max_length=120)
    workspace_id: str | None = Field(default=None, max_length=120)


class AccountOut(BaseModel):
    id: int
    provider_id: str
    provider_name: str
    name: str
    external_org_id: str | None = None
    external_workspace_id: str | None = None
    status: str
    status_message: str | None = None
    is_admin_key: bool
    masked_key_hint: str
    low_balance_threshold: float | None = None
    last_sync_at: datetime | None = None
    created_at: datetime
    is_demo: bool = False


class AccountTestResponse(BaseModel):
    account_id: int
    provider_id: str
    success: bool
    status: str
    message: str
    is_admin_key: bool
    warnings: list[str] = Field(default_factory=list)


class UsageItemOut(BaseModel):
    id: int
    provider_id: str
    provider_name: str
    account_id: int
    account_name: str
    model_id: str
    timestamp: datetime
    period_start: datetime
    period_end: datetime
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    total_tokens: int
    requests_count: int
    original_currency: str
    actual_cost: float | None = None
    estimated_cost: float | None = None
    converted_actual_cost: float | None = None
    converted_estimated_cost: float | None = None
    display_currency: str = "USD"
    cost_type: str
    data_source: str
    data_precision: str
    is_demo: bool = False


class PaginatedUsageOut(BaseModel):
    items: list[UsageItemOut]
    total: int
    page: int
    page_size: int
    is_demo_included: bool


class CostItemOut(BaseModel):
    id: int
    provider_id: str
    provider_name: str
    account_id: int
    account_name: str
    model_id: str | None = None
    period_start: datetime
    period_end: datetime
    amount: float
    original_currency: str
    converted_amount: float
    display_currency: str
    exchange_rate_used: float
    exchange_rate_date: str
    cost_type: Literal["actual", "estimated"]
    data_source: str
    is_demo: bool = False


class PaginatedCostsOut(BaseModel):
    items: list[CostItemOut]
    total: int
    page: int
    page_size: int
    actual_total: float
    estimated_total: float
    display_currency: str
    is_demo_included: bool


class BalanceItemOut(BaseModel):
    account_id: int
    account_name: str
    provider_id: str
    provider_name: str
    is_supported: bool
    available_balance: float | None = None
    total_credits: float | None = None
    used_credits: float | None = None
    original_currency: str
    converted_available_balance: float | None = None
    display_currency: str
    low_balance_threshold: float | None = None
    is_low_balance: bool = False
    status_note: str | None = None
    captured_at: datetime | None = None
    is_demo: bool = False
    billing_url: str | None = None
    top_up_url: str | None = None
    recharge_url: str | None = None
    payment_url: str | None = None

class ModelPriceOut(BaseModel):
    id: int
    provider_id: str
    provider_name: str
    model_id: str
    display_name: str
    context_window: int | None = None
    input_price_per_million: float
    output_price_per_million: float
    cached_input_price_per_million: float | None = None
    currency: str
    price_source: str
    effective_from: datetime
    recorded_at: datetime
    is_current: bool


class DashboardSummaryOut(BaseModel):
    display_currency: str
    exchange_rate_date: str
    exchange_rate_note: str
    actual_billed_cost: float
    estimated_cost: float
    total_combined_spending: float
    confirmed_available_balance: float
    supported_balance_accounts_count: int
    unsupported_balance_accounts_count: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    total_tokens: int
    connected_accounts_count: int
    connected_providers_count: int
    demo_mode_active: bool
    spending_by_provider: list[dict]
    spending_by_model: list[dict]
    recent_activity: list[UsageItemOut]


class TimelinePointOut(BaseModel):
    date: str
    actual_cost: float
    estimated_cost: float
    total_cost: float
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    confirmed_balance: float | None = None


class DashboardTimelineOut(BaseModel):
    display_currency: str
    daily: list[TimelinePointOut]
    monthly: list[dict]


class SyncErrorOut(BaseModel):
    id: int
    provider_id: str
    account_id: int | None = None
    capability: str
    error_code: str
    error_message: str
    created_at: datetime


class SyncJobOut(BaseModel):
    id: int
    account_id: int | None = None
    provider_id: str | None = None
    scope: str
    status: str
    records_synced: int
    started_at: datetime
    finished_at: datetime | None = None
    message: str | None = None
    errors: list[SyncErrorOut] = Field(default_factory=list)


class SyncStatusOut(BaseModel):
    is_running: bool
    last_sync_at: datetime | None = None
    usage_interval_minutes: int
    costs_interval_minutes: int
    balances_interval_minutes: int
    pricing_interval_minutes: int
    recent_jobs: list[SyncJobOut]


class SettingsUpdateRequest(BaseModel):
    default_currency: Literal["USD", "EUR"] = "USD"
    demo_mode: bool = True
    sync_usage_interval_minutes: int = Field(default=15, ge=1, le=1440)
    sync_costs_interval_minutes: int = Field(default=30, ge=1, le=1440)
    sync_balances_interval_minutes: int = Field(default=30, ge=1, le=1440)
    sync_pricing_interval_minutes: int = Field(default=1440, ge=15, le=10080)
    usd_to_eur_rate: float = Field(default=0.92, gt=0.1, lt=5.0)


class SettingsOut(BaseModel):
    default_currency: str
    demo_mode: bool
    sync_usage_interval_minutes: int
    sync_costs_interval_minutes: int
    sync_balances_interval_minutes: int
    sync_pricing_interval_minutes: int
    usd_to_eur_rate: float
    eur_to_usd_rate: float
    exchange_rate_effective_date: str
    exchange_rate_source: str
