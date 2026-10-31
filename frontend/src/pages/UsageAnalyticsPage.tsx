import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, formatMoney, formatTokens } from '../api/client';
import type { DatePreset } from '../types/api';

interface UsageAnalyticsPageProps {
  preset: DatePreset;
  startDate: string;
  endDate: string;
  currency: 'USD' | 'EUR';
}

type GroupDimension = 'provider' | 'account' | 'model' | 'date';

export const UsageAnalyticsPage: React.FC<UsageAnalyticsPageProps> = ({
  preset,
  startDate,
  endDate,
  currency,
}) => {
  const [groupBy, setGroupBy] = useState<GroupDimension>('provider');
  const [providerFilter, setProviderFilter] = useState<string>('');

  const { data: usageData, isLoading } = useQuery({
    queryKey: ['usageAnalytics', preset, startDate, endDate, providerFilter, currency],
    queryFn: () =>
      api.getUsage({
        preset,
        start_date: preset === 'custom' ? startDate : undefined,
        end_date: preset === 'custom' ? endDate : undefined,
        provider_id: providerFilter || undefined,
        currency,
        page: 1,
        page_size: 500,
      }),
  });

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: api.getProviders,
  });

  const groupedRows = useMemo(() => {
    const items = usageData?.items || [];
    const map = new Map<
      string,
      {
        key: string;
        label: string;
        input_tokens: number;
        output_tokens: number;
        cached_input_tokens: number;
        total_tokens: number;
        requests_count: number;
        actual_cost: number;
        estimated_cost: number;
        total_cost: number;
      }
    >();

    for (const item of items) {
      let key = item.provider_name;
      if (groupBy === 'account') key = item.account_name;
      else if (groupBy === 'model') key = item.model_id;
      else if (groupBy === 'date') key = item.timestamp.slice(0, 10);

      const cur = map.get(key) || {
        key,
        label: key,
        input_tokens: 0,
        output_tokens: 0,
        cached_input_tokens: 0,
        total_tokens: 0,
        requests_count: 0,
        actual_cost: 0,
        estimated_cost: 0,
        total_cost: 0,
      };
      cur.input_tokens += item.input_tokens;
      cur.output_tokens += item.output_tokens;
      cur.cached_input_tokens += item.cached_input_tokens;
      cur.total_tokens += item.total_tokens;
      cur.requests_count += item.requests_count;
      const act = item.converted_actual_cost || 0;
      const est = item.converted_estimated_cost || 0;
      cur.actual_cost = Number((cur.actual_cost + act).toFixed(4));
      cur.estimated_cost = Number((cur.estimated_cost + est).toFixed(4));
      cur.total_cost = Number((cur.actual_cost + cur.estimated_cost).toFixed(4));
      map.set(key, cur);
    }

    return Array.from(map.values()).sort((a, b) =>
      groupBy === 'date' ? a.key.localeCompare(b.key) : b.total_cost - a.total_cost
    );
  }, [usageData, groupBy]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Usage Analytics</h1>
          <p className="text-xs text-slate-400">
            Analyze input, output, and cached tokens alongside separated actual and estimated costs.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            aria-label="Filter by provider"
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="rounded-lg border border-[#1f2433] bg-[#11131c] px-3 py-1.5 text-xs text-slate-200"
          >
            <option value="">All Providers</option>
            {(providers || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <div className="inline-flex rounded-lg border border-[#1f2433] bg-[#11131c] p-1">
            {(['provider', 'account', 'model', 'date'] as GroupDimension[]).map((dim) => (
              <button
                key={dim}
                type="button"
                onClick={() => setGroupBy(dim)}
                className={`rounded-md px-3 py-1 text-xs font-medium capitalize transition ${
                  groupBy === dim
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                By {dim}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Interactive Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <h2 className="text-sm font-semibold text-white capitalize">
            Token Consumption Grouped by {groupBy}
          </h2>
          <p className="mb-4 text-xs text-slate-400">
            Input, Output, and Cached Input tokens
          </p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={groupedRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis dataKey="label" stroke="#64748b" fontSize={11} />
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
                <Bar dataKey="cached_input_tokens" name="Cached Input" fill="#10b981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
          <h2 className="text-sm font-semibold text-white capitalize">
            Actual vs. Estimated Costs Grouped by {groupBy}
          </h2>
          <p className="mb-4 text-xs text-slate-400">
            Displayed in {currency}
          </p>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={groupedRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2433" />
                <XAxis dataKey="label" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0e16',
                    borderColor: '#1f2433',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Bar dataKey="actual_cost" name="Actual Billed Cost" stackId="c" fill="#10b981" />
                <Bar dataKey="estimated_cost" name="Estimated Cost" stackId="c" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Grouped Breakdown Table */}
      <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
        <h2 className="mb-4 text-sm font-semibold text-white capitalize">
          Detailed Breakdown by {groupBy}
        </h2>

        {isLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">Loading usage analytics...</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1f2433] text-slate-400">
                  <th className="pb-3 font-medium capitalize">{groupBy}</th>
                  <th className="pb-3 font-medium">Requests</th>
                  <th className="pb-3 font-medium">Input Tokens</th>
                  <th className="pb-3 font-medium">Cached Input</th>
                  <th className="pb-3 font-medium">Output Tokens</th>
                  <th className="pb-3 font-medium">Total Tokens</th>
                  <th className="pb-3 font-medium text-emerald-400">Actual Cost</th>
                  <th className="pb-3 font-medium text-amber-400">Estimated Cost</th>
                  <th className="pb-3 font-medium">Total Spend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2433]">
                {groupedRows.map((row) => (
                  <tr key={row.key} className="hover:bg-[#161a26]">
                    <td className="py-3 font-mono font-semibold text-white">{row.label}</td>
                    <td className="py-3 font-mono text-slate-300">
                      {row.requests_count.toLocaleString()}
                    </td>
                    <td className="py-3 font-mono text-cyan-300">
                      {formatTokens(row.input_tokens)}
                    </td>
                    <td className="py-3 font-mono text-emerald-300">
                      {formatTokens(row.cached_input_tokens)}
                    </td>
                    <td className="py-3 font-mono text-violet-300">
                      {formatTokens(row.output_tokens)}
                    </td>
                    <td className="py-3 font-mono font-semibold text-white">
                      {formatTokens(row.total_tokens)}
                    </td>
                    <td className="py-3 font-mono text-emerald-400">
                      {formatMoney(row.actual_cost, currency)}
                    </td>
                    <td className="py-3 font-mono text-amber-400">
                      {formatMoney(row.estimated_cost, currency)}
                    </td>
                    <td className="py-3 font-mono font-bold text-white">
                      {formatMoney(row.total_cost, currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
