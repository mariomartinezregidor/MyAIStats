import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { api, formatMoney, formatTokens } from '../api/client';
import { useI18n } from '../i18n';
import type { DatePreset } from '../types/api';

interface HistoryPageProps {
  preset: DatePreset;
  startDate: string;
  endDate: string;
  currency: 'USD' | 'EUR';
}

type HistoryTab = 'usage' | 'costs' | 'sync';

export const HistoryPage: React.FC<HistoryPageProps> = ({
  preset,
  startDate,
  endDate,
  currency,
}) => {
  const { t } = useI18n();
  const [tab, setTab] = useState<HistoryTab>('usage');
  const [page, setPage] = useState(1);
  const [providerFilter, setProviderFilter] = useState('');
  const pageSize = 20;

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: api.getProviders,
  });

  const { data: usagePage } = useQuery({
    queryKey: ['historyUsage', preset, startDate, endDate, providerFilter, currency, page],
    queryFn: () =>
      api.getUsage({
        preset,
        start_date: preset === 'custom' ? startDate : undefined,
        end_date: preset === 'custom' ? endDate : undefined,
        provider_id: providerFilter || undefined,
        currency,
        page,
        page_size: pageSize,
      }),
    enabled: tab === 'usage',
  });

  const { data: costsPage } = useQuery({
    queryKey: ['historyCosts', preset, startDate, endDate, providerFilter, currency, page],
    queryFn: () =>
      api.getCosts({
        preset,
        start_date: preset === 'custom' ? startDate : undefined,
        end_date: preset === 'custom' ? endDate : undefined,
        provider_id: providerFilter || undefined,
        currency,
        page,
        page_size: pageSize,
      }),
    enabled: tab === 'costs',
  });

  const { data: syncStatus } = useQuery({
    queryKey: ['syncStatus'],
    queryFn: api.getSyncStatus,
    enabled: tab === 'sync',
  });

  const totalItems =
    tab === 'usage'
      ? usagePage?.total || 0
      : tab === 'costs'
        ? costsPage?.total || 0
        : syncStatus?.recent_jobs.length || 0;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">{t.history.title}</h1>
          <p className="text-xs text-slate-400">
            {t.history.subtitle}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href={`/api/export/csv?dataset=${tab === 'sync' ? 'usage' : tab}&preset=${preset}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1f2433] bg-[#11131c] px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-indigo-500/40"
          >
            <Download className="h-3.5 w-3.5 text-indigo-400" />
            {t.history.exportCsv}
          </a>
          <a
            href={`/api/export/json?dataset=${tab === 'sync' ? 'usage' : tab}&preset=${preset}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1f2433] bg-[#11131c] px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-indigo-500/40"
          >
            <Download className="h-3.5 w-3.5 text-emerald-400" />
            {t.history.exportJson}
          </a>
        </div>
      </div>

      {/* Tabs & Provider Filter */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-xl border border-[#1f2433] bg-[#11131c] p-1">
          {(
            [
              { id: 'usage', label: t.history.usageRecords },
              { id: 'costs', label: t.history.costRecords },
              { id: 'sync', label: t.history.syncAuditLog },
            ] as { id: HistoryTab; label: string }[]
          ).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => {
                setTab(t.id);
                setPage(1);
              }}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition ${
                tab === t.id
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab !== 'sync' && (
          <select
            aria-label="Filter history by provider"
            value={providerFilter}
            onChange={(e) => {
              setProviderFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-[#1f2433] bg-[#11131c] px-3 py-1.5 text-xs text-slate-200"
          >
            <option value="">{t.analytics.allProviders}</option>
            {(providers || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Content Table */}
      <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
        {tab === 'usage' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1f2433] text-slate-400">
                  <th className="pb-3 font-medium">{t.history.timestampUtc}</th>
                  <th className="pb-3 font-medium">Provider / Account</th>
                  <th className="pb-3 font-medium">{t.history.model}</th>
                  <th className="pb-3 font-medium">{t.history.input}</th>
                  <th className="pb-3 font-medium">{t.history.cached}</th>
                  <th className="pb-3 font-medium">{t.history.output}</th>
                  <th className="pb-3 font-medium">{t.history.costCategory}</th>
                  <th className="pb-3 font-medium">{t.history.amount} ({currency})</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2433]">
                {(usagePage?.items || []).map((u) => (
                  <tr key={u.id} className="hover:bg-[#161a26]">
                    <td className="py-3 font-mono text-[11px] text-slate-400">
                      {u.timestamp.slice(0, 19).replace('T', ' ')}
                    </td>
                    <td className="py-3">
                      <div className="font-medium text-white">{u.provider_name}</div>
                      <div className="text-[11px] text-slate-400">{u.account_name}</div>
                    </td>
                    <td className="py-3 font-mono text-indigo-300">{u.model_id}</td>
                    <td className="py-3 font-mono text-cyan-300">{formatTokens(u.input_tokens)}</td>
                    <td className="py-3 font-mono text-emerald-300">
                      {formatTokens(u.cached_input_tokens)}
                    </td>
                    <td className="py-3 font-mono text-violet-300">
                      {formatTokens(u.output_tokens)}
                    </td>
                    <td className="py-3">
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          u.cost_type === 'actual'
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : 'bg-amber-500/15 text-amber-300'
                        }`}
                      >
                        {u.cost_type}
                      </span>
                    </td>
                    <td className="py-3 font-mono font-semibold text-white">
                      {formatMoney(
                        u.converted_actual_cost ?? u.converted_estimated_cost,
                        u.display_currency
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'costs' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1f2433] text-slate-400">
                  <th className="pb-3 font-medium">{t.history.periodStart}</th>
                  <th className="pb-3 font-medium">Provider / Account</th>
                  <th className="pb-3 font-medium">{t.history.lineItem}</th>
                  <th className="pb-3 font-medium">{t.history.category}</th>
                  <th className="pb-3 font-medium">{t.history.originalAmount}</th>
                  <th className="pb-3 font-medium">{t.history.converted} ({currency})</th>
                  <th className="pb-3 font-medium">{t.history.fxRateDate}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2433]">
                {(costsPage?.items || []).map((c) => (
                  <tr key={c.id} className="hover:bg-[#161a26]">
                    <td className="py-3 font-mono text-[11px] text-slate-400">
                      {c.period_start.slice(0, 10)}
                    </td>
                    <td className="py-3">
                      <div className="font-medium text-white">{c.provider_name}</div>
                      <div className="text-[11px] text-slate-400">{c.account_name}</div>
                    </td>
                    <td className="py-3 font-mono text-indigo-300">{c.model_id || 'Org Billing'}</td>
                    <td className="py-3">
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
                          c.cost_type === 'actual'
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : 'bg-amber-500/15 text-amber-300'
                        }`}
                      >
                        {c.cost_type}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-slate-300">
                      {formatMoney(c.amount, c.original_currency)}
                    </td>
                    <td className="py-3 font-mono font-semibold text-white">
                      {formatMoney(c.converted_amount, c.display_currency)}
                    </td>
                    <td className="py-3 font-mono text-[11px] text-slate-400">
                      {c.exchange_rate_used} ({c.exchange_rate_date})
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {tab === 'sync' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1f2433] text-slate-400">
                  <th className="pb-3 font-medium">{t.history.startedAt}</th>
                  <th className="pb-3 font-medium">Provider</th>
                  <th className="pb-3 font-medium">{t.history.scope}</th>
                  <th className="pb-3 font-medium">{t.history.status}</th>
                  <th className="pb-3 font-medium">{t.history.recordsSynced}</th>
                  <th className="pb-3 font-medium">{t.history.messageError}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2433]">
                {(syncStatus?.recent_jobs || []).map((j) => (
                  <tr key={j.id} className="hover:bg-[#161a26]">
                    <td className="py-3 font-mono text-[11px] text-slate-400">
                      {j.started_at.slice(0, 19).replace('T', ' ')}
                    </td>
                    <td className="py-3 font-semibold uppercase text-indigo-300">
                      {j.provider_id || 'All'}
                    </td>
                    <td className="py-3 font-mono text-slate-300">{j.scope}</td>
                    <td className="py-3">
                      <span className="rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                        {j.status}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-white">{j.records_synced}</td>
                    <td className="py-3 text-slate-300">{j.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Controls */}
        {tab !== 'sync' && (
          <div className="mt-4 flex items-center justify-between border-t border-[#1f2433] pt-4 text-xs text-slate-400">
            <div>
              {t.history.showingPage} <span className="font-semibold text-white">{page}</span> {t.history.of}{' '}
              <span className="font-semibold text-white">{totalPages}</span> ({totalItems} {t.history.totalRecords})
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="inline-flex items-center gap-1 rounded-lg border border-[#1f2433] bg-[#0c0e16] px-2.5 py-1 text-slate-200 disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                {t.history.prev}
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="inline-flex items-center gap-1 rounded-lg border border-[#1f2433] bg-[#0c0e16] px-2.5 py-1 text-slate-200 disabled:opacity-40"
              >
                {t.history.next}
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
