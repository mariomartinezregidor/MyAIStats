import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  Coins,
  Cpu,
  DollarSign,
  Layers,
  ShieldAlert,
  Wallet,
} from 'lucide-react';
import { api, formatMoney, formatTokens } from '../api/client';
import type { DatePreset } from '../types/api';

interface OverviewPageProps {
  preset: DatePreset;
  startDate: string;
  endDate: string;
  currency: 'USD' | 'EUR';
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  preset,
  startDate,
  endDate,
  currency,
}) => {
  const { data: summary, isLoading: loadingSummary } = useQuery({
    queryKey: ['dashboardSummary', preset, startDate, endDate, currency],
    queryFn: () =>
      api.getDashboardSummary({
        preset,
        start_date: preset === 'custom' ? startDate : undefined,
        end_date: preset === 'custom' ? endDate : undefined,
        currency,
      }),
  });

  const { data: timeline, isLoading: loadingTimeline } = useQuery({
    queryKey: ['dashboardTimeline', preset, startDate, endDate, currency],
    queryFn: () =>
      api.getDashboardTimeline({
        preset,
        start_date: preset === 'custom' ? startDate : undefined,
        end_date: preset === 'custom' ? endDate : undefined,
        currency,
      }),
  });

  const { data: syncStatus } = useQuery({
    queryKey: ['syncStatus'],
    queryFn: api.getSyncStatus,
  });

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.getAccounts(true),
  });

  if (loadingSummary || loadingTimeline || !summary || !timeline) {
    return (
      <div className="space-y-4">
        <div className="h-28 animate-pulse rounded-xl border border-[#1f2433] bg-[#11131c]" />
        <div className="h-80 animate-pulse rounded-xl border border-[#1f2433] bg-[#11131c]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Overview Dashboard
          </h1>
          <p className="text-xs text-slate-400">
            Unified API spending, confirmed balances, and token analytics •{' '}
            <span className="font-mono text-slate-300">{summary.exchange_rate_note}</span>
          </p>
        </div>
        {summary.demo_mode_active && (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-medium text-amber-300">
            Includes Clearly Labeled [DEMO] Data
          </span>
        )}
      </div>

      {/* 4 Primary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {/* Card 1: Total Spending (strictly split into Actual vs Estimated) */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Total Spending
            </span>
            <DollarSign className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {formatMoney(summary.total_combined_spending, summary.display_currency)}
          </div>
          <div className="mt-3 space-y-1 border-t border-[#1f2433] pt-2.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Actual Billed Costs:
              </span>
              <span className="font-mono font-semibold text-slate-200">
                {formatMoney(summary.actual_billed_cost, summary.display_currency)}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-amber-400">
                <span className="h-2 w-2 rounded-full bg-amber-400" />
                Estimated Costs:
              </span>
              <span className="font-mono font-semibold text-slate-200">
                {formatMoney(summary.estimated_cost, summary.display_currency)}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Confirmed Available Balance */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Confirmed Available Balance
            </span>
            <Wallet className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-400">
            {formatMoney(summary.confirmed_available_balance, summary.display_currency)}
          </div>
          <div className="mt-3 space-y-1 border-t border-[#1f2433] pt-2.5 text-xs text-slate-400">
            <div className="flex justify-between">
              <span>Supported Balance Accounts:</span>
              <span className="font-mono text-slate-200">
                {summary.supported_balance_accounts_count}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Unsupported API Balance:</span>
              <span className="font-mono text-slate-400">
                {summary.unsupported_balance_accounts_count} (Never guessed)
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Input Tokens */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Input Tokens
            </span>
            <ArrowUpRight className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {formatTokens(summary.input_tokens)}
          </div>
          <div className="mt-3 space-y-1 border-t border-[#1f2433] pt-2.5 text-xs text-slate-400">
            <div className="flex justify-between">
              <span>Cached Input Tokens:</span>
              <span className="font-mono text-cyan-300">
                {formatTokens(summary.cached_input_tokens)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Exact Count:</span>
              <span className="font-mono text-slate-300">
                {summary.input_tokens.toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: Output Tokens */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Output Tokens
            </span>
            <ArrowDownRight className="h-4 w-4 text-violet-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">
            {formatTokens(summary.output_tokens)}
          </div>
          <div className="mt-3 space-y-1 border-t border-[#1f2433] pt-2.5 text-xs text-slate-400">
            <div className="flex justify-between">
              <span>Total Combined Tokens:</span>
              <span className="font-mono text-violet-300">
                {formatTokens(summary.total_tokens)}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Exact Count:</span>
              <span className="font-mono text-slate-300">
                {summary.output_tokens.toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row 1: Daily Spending & Monthly Spending */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">
                Daily Spending (Actual Billed vs. Estimated)
              </h2>
              <p className="text-xs text-slate-400">
                Never mixes official billed charges with calculated token estimates
              </p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeline.daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0e16',
                    borderColor: '#1f2433',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="actual_cost"
                  name="Actual Billed Cost"
                  stackId="1"
                  stroke="#10b981"
                  fill="#10b981"
                  fillOpacity={0.25}
                />
                <Area
                  type="monotone"
                  dataKey="estimated_cost"
                  name="Estimated Cost"
                  stackId="1"
                  stroke="#f59e0b"
                  fill="#f59e0b"
                  fillOpacity={0.25}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <h2 className="text-sm font-semibold text-white">Monthly Spending</h2>
          <p className="mb-4 text-xs text-slate-400">
            Aggregated monthly Actual vs. Estimated spend
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeline.monthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis dataKey="month" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0e16',
                    borderColor: '#1f2433',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Bar dataKey="actual_cost" name="Actual" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar
                  dataKey="estimated_cost"
                  name="Estimated"
                  fill="#f59e0b"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2: Spending by Provider & Spending by Model */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <h2 className="text-sm font-semibold text-white">Spending by Provider</h2>
          <p className="mb-4 text-xs text-slate-400">
            Breakdown of Actual vs. Estimated costs across providers
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary.spending_by_provider} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis type="number" stroke="#64748b" fontSize={11} />
                <YAxis
                  type="category"
                  dataKey="provider_name"
                  stroke="#94a3b8"
                  fontSize={11}
                  width={95}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0e16',
                    borderColor: '#1f2433',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Bar dataKey="actual_cost" name="Actual Cost" stackId="a" fill="#6366f1" />
                <Bar dataKey="estimated_cost" name="Estimated Cost" stackId="a" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <h2 className="text-sm font-semibold text-white">Spending by Model</h2>
          <p className="mb-4 text-xs text-slate-400">
            Top AI models ranked by cost in {summary.display_currency}
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary.spending_by_model.slice(0, 6)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis type="number" stroke="#64748b" fontSize={11} />
                <YAxis
                  type="category"
                  dataKey="model_id"
                  stroke="#94a3b8"
                  fontSize={10}
                  width={135}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0e16',
                    borderColor: '#1f2433',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Bar dataKey="actual_cost" name="Actual" stackId="m" fill="#10b981" />
                <Bar dataKey="estimated_cost" name="Estimated" stackId="m" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 3: Token Consumption & Confirmed Balance History */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <h2 className="text-sm font-semibold text-white">Daily Token Consumption</h2>
          <p className="mb-4 text-xs text-slate-400">
            Input tokens, Output tokens, and Cached input tokens
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeline.daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0e16',
                    borderColor: '#1f2433',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Bar dataKey="input_tokens" name="Input Tokens" fill="#06b6d4" />
                <Bar dataKey="output_tokens" name="Output Tokens" fill="#8b5cf6" />
                <Bar dataKey="cached_input_tokens" name="Cached Tokens" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <h2 className="text-sm font-semibold text-white">Confirmed Balance History</h2>
          <p className="mb-4 text-xs text-slate-400">
            Available credit trajectory for providers with official balance APIs
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeline.daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0e16',
                    borderColor: '#1f2433',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="confirmed_balance"
                  name="Confirmed Balance"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom Row: Connected Accounts Status, Recent Sync Jobs & Recent Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Connected Accounts */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Connected Accounts</h2>
            <Layers className="h-4 w-4 text-indigo-400" />
          </div>
          <div className="space-y-2.5">
            {(accounts || []).map((acc) => (
              <div
                key={acc.id}
                className="flex items-center justify-between rounded-lg border border-[#1f2433] bg-[#0c0e16] px-3 py-2 text-xs"
              >
                <div>
                  <div className="font-medium text-slate-200">{acc.name}</div>
                  <div className="text-[11px] text-slate-400">
                    {acc.provider_name} • <span className="font-mono">{acc.masked_key_hint}</span>
                  </div>
                </div>
                <span
                  className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    acc.status === 'connected'
                      ? 'bg-emerald-500/15 text-emerald-300'
                      : 'bg-rose-500/15 text-rose-300'
                  }`}
                >
                  <CheckCircle2 className="h-3 w-3" />
                  {acc.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Sync Jobs */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Recent Synchronization Jobs</h2>
            <Cpu className="h-4 w-4 text-cyan-400" />
          </div>
          <div className="space-y-2.5">
            {(syncStatus?.recent_jobs || []).slice(0, 5).map((job) => (
              <div
                key={job.id}
                className="rounded-lg border border-[#1f2433] bg-[#0c0e16] px-3 py-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold uppercase text-indigo-300">
                    {job.provider_id || 'all'} ({job.scope})
                  </span>
                  <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
                    {job.status}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-slate-400">{job.message}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Recent Token Activity</h2>
            <Coins className="h-4 w-4 text-amber-400" />
          </div>
          <div className="space-y-2">
            {summary.recent_activity.slice(0, 5).map((act) => (
              <div
                key={act.id}
                className="flex items-center justify-between rounded-lg border border-[#1f2433] bg-[#0c0e16] px-3 py-2 text-xs"
              >
                <div>
                  <div className="font-mono font-medium text-slate-200">{act.model_id}</div>
                  <div className="text-[11px] text-slate-400">
                    {act.provider_name} • {formatTokens(act.total_tokens)} tokens
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-semibold text-slate-200">
                    {formatMoney(
                      act.converted_actual_cost ?? act.converted_estimated_cost,
                      act.display_currency
                    )}
                  </div>
                  <span
                    className={`text-[10px] font-semibold uppercase ${
                      act.cost_type === 'actual' ? 'text-emerald-400' : 'text-amber-400'
                    }`}
                  >
                    {act.cost_type}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
