import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nProvider } from '../i18n';
import { AppContent } from '../App';

const mockSummary = {
  display_currency: 'USD',
  exchange_rate_date: '2026-10-31',
  exchange_rate_note: '1 USD = 1.0 USD (source: identity, date: 2026-10-31)',
  actual_billed_cost: 184.25,
  estimated_cost: 32.5,
  total_combined_spending: 216.75,
  confirmed_available_balance: 83.15,
  supported_balance_accounts_count: 2,
  unsupported_balance_accounts_count: 2,
  input_tokens: 14500000,
  output_tokens: 4200000,
  cached_input_tokens: 3100000,
  total_tokens: 18700000,
  connected_accounts_count: 4,
  connected_providers_count: 4,
  demo_mode_active: true,
  spending_by_provider: [
    {
      provider_id: 'openai',
      provider_name: 'OpenAI',
      actual_cost: 82.5,
      estimated_cost: 18.0,
      total_cost: 100.5,
      tokens: 8000000,
    },
  ],
  spending_by_model: [
    {
      model_id: 'gpt-4o',
      provider_name: 'OpenAI',
      actual_cost: 82.5,
      estimated_cost: 0,
      total_cost: 82.5,
      input_tokens: 5000000,
      output_tokens: 1500000,
      cached_input_tokens: 1200000,
      total_tokens: 6500000,
    },
  ],
  recent_activity: [],
};

const mockTimeline = {
  display_currency: 'USD',
  daily: [
    {
      date: '2026-10-30',
      actual_cost: 6.2,
      estimated_cost: 1.1,
      total_cost: 7.3,
      input_tokens: 450000,
      output_tokens: 120000,
      cached_input_tokens: 90000,
      confirmed_balance: 83.15,
    },
  ],
  monthly: [
    {
      month: '2026-10',
      actual_cost: 184.25,
      estimated_cost: 32.5,
      total_cost: 216.75,
      tokens: 18700000,
    },
  ],
};

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string) => {
      if (url.includes('/dashboard/summary')) {
        return { ok: true, status: 200, json: async () => mockSummary };
      }
      if (url.includes('/dashboard/timeline')) {
        return { ok: true, status: 200, json: async () => mockTimeline };
      }
      if (url.includes('/sync/status')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            is_running: false,
            last_sync_at: '2026-10-31T10:00:00Z',
            usage_interval_minutes: 15,
            costs_interval_minutes: 30,
            balances_interval_minutes: 30,
            pricing_interval_minutes: 1440,
            recent_jobs: [],
          }),
        };
      }
      if (url.includes('/settings')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            default_currency: 'USD',
            demo_mode: true,
            sync_usage_interval_minutes: 15,
            sync_costs_interval_minutes: 30,
            sync_balances_interval_minutes: 30,
            sync_pricing_interval_minutes: 1440,
            usd_to_eur_rate: 0.92,
            eur_to_usd_rate: 1.0869,
            exchange_rate_effective_date: '2026-10-31',
            exchange_rate_source: 'ecb_reference',
          }),
        };
      }
      if (url.includes('/accounts')) {
        return {
          ok: true,
          status: 200,
          json: async () => [
            {
              id: -101,
              provider_id: 'openai',
              provider_name: 'OpenAI',
              name: '[DEMO] OpenAI Production Org',
              external_org_id: 'org-demo',
              status: 'connected',
              status_message: 'Demo Mode',
              is_admin_key: true,
              masked_key_hint: 'sk-adm...demo',
              low_balance_threshold: null,
              last_sync_at: '2026-10-31T10:00:00Z',
              created_at: '2026-10-01T00:00:00Z',
              is_demo: true,
            },
          ],
        };
      }
      if (url.includes('/balances')) {
        return {
          ok: true,
          status: 200,
          json: async () => [
            {
              account_id: -102,
              account_name: '[DEMO] OpenRouter Multi-Model Router',
              provider_id: 'openrouter',
              provider_name: 'OpenRouter',
              is_supported: true,
              available_balance: 64.4,
              total_credits: 120.0,
              used_credits: 55.6,
              original_currency: 'USD',
              converted_available_balance: 64.4,
              display_currency: 'USD',
              low_balance_threshold: 15.0,
              is_low_balance: false,
              status_note: 'Confirmed via OpenRouter /api/v1/credits',
              captured_at: '2026-10-31T10:00:00Z',
              is_demo: true,
            },
            {
              account_id: -101,
              account_name: '[DEMO] OpenAI Production Org',
              provider_id: 'openai',
              provider_name: 'OpenAI',
              is_supported: false,
              available_balance: null,
              total_credits: null,
              used_credits: null,
              original_currency: 'USD',
              converted_available_balance: null,
              display_currency: 'USD',
              low_balance_threshold: null,
              is_low_balance: false,
              status_note: 'Unsupported by official OpenAI public API',
              captured_at: '2026-10-31T10:00:00Z',
              is_demo: true,
            },
          ],
        };
      }
      return { ok: true, status: 200, json: async () => [] };
    })
  );
});

describe('MyAIStats Dashboard UI', () => {
  it('renders Overview dashboard with separated Actual vs Estimated costs and Demo labels', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <I18nProvider>
          <MemoryRouter initialEntries={['/']}>
            <AppContent />
          </MemoryRouter>
        </I18nProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Overview Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('Actual Billed Costs:')).toBeInTheDocument();
    expect(screen.getByText('Estimated Costs:')).toBeInTheDocument();
    expect(screen.getByText('$184.25 USD')).toBeInTheDocument();
    expect(screen.getByText('$32.50 USD')).toBeInTheDocument();
    expect(screen.getByText('Includes Clearly Labeled [DEMO] Data')).toBeInTheDocument();
  });

  it('renders Credits & Balance page distinguishing confirmed vs unsupported balances', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <I18nProvider>
          <MemoryRouter initialEntries={['/balances']}>
            <AppContent />
          </MemoryRouter>
        </I18nProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Credits & Confirmed Balances')).toBeInTheDocument();
    });

    expect(screen.getByText('$64.40 USD')).toBeInTheDocument();
    expect(screen.getByText('Balance API Unsupported')).toBeInTheDocument();
  });

  it('renders Providers page with account connection form and capability matrix', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <I18nProvider>
          <MemoryRouter initialEntries={['/providers']}>
            <AppContent />
          </MemoryRouter>
        </I18nProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Providers & Accounts')).toBeInTheDocument();
    });

    expect(screen.getByText('Connect Provider Account')).toBeInTheDocument();
    expect(screen.getByText('Verified Official Provider Capability Matrix')).toBeInTheDocument();
  });

  it('renders Settings page with currency, sync intervals, exports, and SQLite backup controls', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <I18nProvider>
          <MemoryRouter initialEntries={['/settings']}>
            <AppContent />
          </MemoryRouter>
        </I18nProvider>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Settings, Exports & Local Data Ownership')).toBeInTheDocument();
    });

    expect(screen.getByText('Download SQLite Backup (.db)')).toBeInTheDocument();
    expect(screen.getByText('Local-First Security Guarantees')).toBeInTheDocument();
  });
});
