from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProviderCapabilities(BaseModel):
    supports_connection_test: bool = True
    supports_usage: bool = False
    supports_costs: bool = False
    supports_balance: bool = False
    supports_pricing: bool = False
    requires_admin_key_for_usage: bool = False
    capability_notes: str = ""


class ConnectorCredentials(BaseModel):
    api_key: str
    extra_secret: str | None = None
    organization_id: str | None = None


class ConnectionTestResult(BaseModel):
    success: bool
    status: Literal["connected", "error", "partial"]
    message: str
    is_admin_key: bool = False
    detected_models_count: int | None = None
    warnings: list[str] = Field(default_factory=list)


class NormalizedUsageRecord(BaseModel):
    model_id: str
    timestamp: datetime
    period_start: datetime
    period_end: datetime
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    total_tokens: int = 0
    requests_count: int = 1
    currency: str = "USD"
    actual_cost: float | None = None
    data_source: str = "official_api"
    data_precision: str = "bucket_1d"
    external_record_id: str


class NormalizedCostRecord(BaseModel):
    model_id: str | None = None
    period_start: datetime
    period_end: datetime
    amount: float
    currency: str = "USD"
    cost_type: Literal["actual", "estimated"] = "actual"
    data_source: str = "official_billing_api"
    external_record_id: str


class NormalizedBalanceSnapshot(BaseModel):
    available_balance: float | None = None
    total_credits: float | None = None
    used_credits: float | None = None
    currency: str = "USD"
    is_supported: bool = True
    status_note: str | None = None
    data_source: str = "official_api"


class NormalizedModelPrice(BaseModel):
    model_id: str
    display_name: str
    context_window: int | None = None
    input_price_per_million: float
    output_price_per_million: float
    cached_input_price_per_million: float | None = None
    currency: str = "USD"
    price_source: str = "official_api"
