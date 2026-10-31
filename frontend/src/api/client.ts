import type {
  AccountInfo,
  AppSettings,
  BalanceItem,
  CostItem,
  DashboardSummary,
  DashboardTimeline,
  ModelPriceItem,
  ProviderInfo,
  SyncJob,
  SyncStatus,
  UsageItem,
} from '../types/api';

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers || {}),
    },
    ...options,
  });
  if (!res.ok) {
    let errText = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) errText = String(data.detail);
    } catch {
      // ignore json parse failure
    }
    throw new Error(errText);
  }
  if (res.status === 204) {
    return undefined as unknown as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  getProviders: () => request<ProviderInfo[]>('/providers'),
  getAccounts: (includeDemo = true) =>
    request<AccountInfo[]>(`/accounts?include_demo=${includeDemo}`),
  connectAccount: (payload: {
    provider_id: string;
    name: string;
    api_key: string;
    organization_id?: string;
    low_balance_threshold?: number | null;
  }) =>
    request<AccountInfo>('/accounts/connect', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  rotateCredentials: (
    accountId: number,
    payload: { api_key: string; organization_id?: string }
  ) =>
    request<AccountInfo>(`/accounts/${accountId}/credentials`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  testAccount: (accountId: number) =>
    request<{
      account_id: number;
      provider_id: string;
      success: boolean;
      status: string;
      message: string;
      is_admin_key: boolean;
      warnings: string[];
    }>(`/accounts/${accountId}/test`, { method: 'POST' }),
  syncAccount: (accountId: number, scope = 'full') =>
    request<SyncJob>(`/accounts/${accountId}/sync?scope=${scope}`, {
      method: 'POST',
    }),
  deleteAccount: (accountId: number) =>
    request<void>(`/accounts/${accountId}`, { method: 'DELETE' }),
  getDashboardSummary: (params: {
    preset?: string;
    start_date?: string;
    end_date?: string;
    provider_id?: string;
    currency?: string;
  }) => {
    const q = new URLSearchParams();
    if (params.preset) q.set('preset', params.preset);
    if (params.start_date) q.set('start_date', params.start_date);
    if (params.end_date) q.set('end_date', params.end_date);
    if (params.provider_id) q.set('provider_id', params.provider_id);
    if (params.currency) q.set('currency', params.currency);
    return request<DashboardSummary>(`/dashboard/summary?${q.toString()}`);
  },
  getDashboardTimeline: (params: {
    preset?: string;
    start_date?: string;
    end_date?: string;
    provider_id?: string;
    currency?: string;
  }) => {
    const q = new URLSearchParams();
    if (params.preset) q.set('preset', params.preset);
    if (params.start_date) q.set('start_date', params.start_date);
    if (params.end_date) q.set('end_date', params.end_date);
    if (params.provider_id) q.set('provider_id', params.provider_id);
    if (params.currency) q.set('currency', params.currency);
    return request<DashboardTimeline>(`/dashboard/timeline?${q.toString()}`);
  },
  getUsage: (params: {
    preset?: string;
    start_date?: string;
    end_date?: string;
    provider_id?: string;
    account_id?: number;
    model_id?: string;
    currency?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.preset) q.set('preset', params.preset);
    if (params.start_date) q.set('start_date', params.start_date);
    if (params.end_date) q.set('end_date', params.end_date);
    if (params.provider_id) q.set('provider_id', params.provider_id);
    if (params.account_id !== undefined) q.set('account_id', String(params.account_id));
    if (params.model_id) q.set('model_id', params.model_id);
    if (params.currency) q.set('currency', params.currency);
    if (params.page) q.set('page', String(params.page));
    if (params.page_size) q.set('page_size', String(params.page_size));
    return request<{
      items: UsageItem[];
      total: number;
      page: number;
      page_size: number;
      is_demo_included: boolean;
    }>(`/usage?${q.toString()}`);
  },
  getCosts: (params: {
    preset?: string;
    start_date?: string;
    end_date?: string;
    provider_id?: string;
    cost_type?: string;
    currency?: string;
    page?: number;
    page_size?: number;
  }) => {
    const q = new URLSearchParams();
    if (params.preset) q.set('preset', params.preset);
    if (params.start_date) q.set('start_date', params.start_date);
    if (params.end_date) q.set('end_date', params.end_date);
    if (params.provider_id) q.set('provider_id', params.provider_id);
    if (params.cost_type) q.set('cost_type', params.cost_type);
    if (params.currency) q.set('currency', params.currency);
    if (params.page) q.set('page', String(params.page));
    if (params.page_size) q.set('page_size', String(params.page_size));
    return request<{
      items: CostItem[];
      total: number;
      page: number;
      page_size: number;
      actual_total: number;
      estimated_total: number;
      display_currency: string;
      is_demo_included: boolean;
    }>(`/costs?${q.toString()}`);
  },
  getBalances: (currency?: string) =>
    request<BalanceItem[]>(currency ? `/balances?currency=${currency}` : '/balances'),
  getPricing: (providerId?: string, includeHistory = false) => {
    const q = new URLSearchParams();
    if (providerId) q.set('provider_id', providerId);
    if (includeHistory) q.set('include_history', 'true');
    return request<ModelPriceItem[]>(`/pricing?${q.toString()}`);
  },
  getSyncStatus: () => request<SyncStatus>('/sync/status'),
  runGlobalSync: (scope = 'full') =>
    request<SyncJob[]>(`/sync/run?scope=${scope}`, { method: 'POST' }),
  getSettings: () => request<AppSettings>('/settings'),
  updateSettings: (payload: {
    default_currency: 'USD' | 'EUR';
    demo_mode: boolean;
    sync_usage_interval_minutes: number;
    sync_costs_interval_minutes: number;
    sync_balances_interval_minutes: number;
    sync_pricing_interval_minutes: number;
    usd_to_eur_rate: number;
  }) =>
    request<AppSettings>('/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
};

export function formatMoney(amount: number | null | undefined, currency = 'USD'): string {
  if (amount === null || amount === undefined) return '—';
  const symbol = currency === 'EUR' ? '€' : '$';
  return `${symbol}${amount.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  })} ${currency}`;
}

export function formatTokens(tokens: number | null | undefined): string {
  if (tokens === null || tokens === undefined) return '0';
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(2)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toLocaleString('en-US');
}
