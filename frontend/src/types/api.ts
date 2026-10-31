export type DatePreset = 'today' | '7d' | '30d' | 'current_month' | 'previous_month' | 'custom';

export interface ProviderInfo {
  id: string;
  name: string;
  category_priority: number;
  api_base_url: string;
  docs_url: string;
  auth_instructions: string;
  supports_connection_test: boolean;
  supports_usage: boolean;
  supports_costs: boolean;
  supports_balance: boolean;
  supports_pricing: boolean;
  requires_admin_key_for_usage: boolean;
  capability_notes: string;
  connected_accounts_count: number;
}

export interface AccountInfo {
  id: number;
  provider_id: string;
  provider_name: string;
  name: string;
  external_org_id: string | null;
  external_workspace_id: string | null;
  status: 'connected' | 'error' | 'unverified' | 'partial';
  status_message: string | null;
  is_admin_key: boolean;
  masked_key_hint: string;
  low_balance_threshold: number | null;
  last_sync_at: string | null;
  created_at: string;
  is_demo: boolean;
}

export interface UsageItem {
  id: number;
  provider_id: string;
  provider_name: string;
  account_id: number;
  account_name: string;
  model_id: string;
  timestamp: string;
  period_start: string;
  period_end: string;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  total_tokens: number;
  requests_count: number;
  original_currency: string;
  actual_cost: number | null;
  estimated_cost: number | null;
  converted_actual_cost: number | null;
  converted_estimated_cost: number | null;
  display_currency: string;
  cost_type: 'actual' | 'estimated' | 'none';
  data_source: string;
  data_precision: string;
  is_demo: boolean;
}

export interface CostItem {
  id: number;
  provider_id: string;
  provider_name: string;
  account_id: number;
  account_name: string;
  model_id: string | null;
  period_start: string;
  period_end: string;
  amount: number;
  original_currency: string;
  converted_amount: number;
  display_currency: string;
  exchange_rate_used: number;
  exchange_rate_date: string;
  cost_type: 'actual' | 'estimated';
  data_source: string;
  is_demo: boolean;
}

export interface BalanceItem {
  account_id: number;
  account_name: string;
  provider_id: string;
  provider_name: string;
  is_supported: boolean;
  available_balance: number | null;
  total_credits: number | null;
  used_credits: number | null;
  original_currency: string;
  converted_available_balance: number | null;
  display_currency: string;
  low_balance_threshold: number | null;
  is_low_balance: boolean;
  status_note: string | null;
  captured_at: string | null;
  is_demo: boolean;
}

export interface ModelPriceItem {
  id: number;
  provider_id: string;
  provider_name: string;
  model_id: string;
  display_name: string;
  context_window: number | null;
  input_price_per_million: number;
  output_price_per_million: number;
  cached_input_price_per_million: number | null;
  currency: string;
  price_source: string;
  effective_from: string;
  recorded_at: string;
  is_current: boolean;
}

export interface DashboardSummary {
  display_currency: string;
  exchange_rate_date: string;
  exchange_rate_note: string;
  actual_billed_cost: number;
  estimated_cost: number;
  total_combined_spending: number;
  confirmed_available_balance: number;
  supported_balance_accounts_count: number;
  unsupported_balance_accounts_count: number;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  total_tokens: number;
  connected_accounts_count: number;
  connected_providers_count: number;
  demo_mode_active: boolean;
  spending_by_provider: Array<{
    provider_id: string;
    provider_name: string;
    actual_cost: number;
    estimated_cost: number;
    total_cost: number;
    tokens: number;
  }>;
  spending_by_model: Array<{
    model_id: string;
    provider_name: string;
    actual_cost: number;
    estimated_cost: number;
    total_cost: number;
    input_tokens: number;
    output_tokens: number;
    cached_input_tokens: number;
    total_tokens: number;
  }>;
  recent_activity: UsageItem[];
}

export interface TimelinePoint {
  date: string;
  actual_cost: number;
  estimated_cost: number;
  total_cost: number;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  confirmed_balance: number | null;
}

export interface DashboardTimeline {
  display_currency: string;
  daily: TimelinePoint[];
  monthly: Array<{
    month: string;
    actual_cost: number;
    estimated_cost: number;
    total_cost: number;
    tokens: number;
  }>;
}

export interface SyncJob {
  id: number;
  account_id: number | null;
  provider_id: string | null;
  scope: string;
  status: string;
  records_synced: number;
  started_at: string;
  finished_at: string | null;
  message: string | null;
  errors: Array<{
    id: number;
    provider_id: string;
    account_id: number | null;
    capability: string;
    error_code: string;
    error_message: string;
    created_at: string;
  }>;
}

export interface SyncStatus {
  is_running: boolean;
  last_sync_at: string | null;
  usage_interval_minutes: number;
  costs_interval_minutes: number;
  balances_interval_minutes: number;
  pricing_interval_minutes: number;
  recent_jobs: SyncJob[];
}

export interface AppSettings {
  default_currency: 'USD' | 'EUR';
  demo_mode: boolean;
  sync_usage_interval_minutes: number;
  sync_costs_interval_minutes: number;
  sync_balances_interval_minutes: number;
  sync_pricing_interval_minutes: number;
  usd_to_eur_rate: number;
  eur_to_usd_rate: number;
  exchange_rate_effective_date: string;
  exchange_rate_source: string;
}
