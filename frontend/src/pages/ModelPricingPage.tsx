import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Cpu, Search } from 'lucide-react';
import { api } from '../api/client';
import { useI18n } from '../i18n';

export const ModelPricingPage: React.FC = () => {
  const { t } = useI18n();
  const [providerFilter, setProviderFilter] = useState('');
  const [search, setSearch] = useState('');
  const [includeHistory, setIncludeHistory] = useState(false);

  const { data: prices, isLoading } = useQuery({
    queryKey: ['pricing', providerFilter, includeHistory],
    queryFn: () => api.getPricing(providerFilter || undefined, includeHistory),
  });

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: api.getProviders,
  });

  const filtered = (prices || []).filter((p) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      p.model_id.toLowerCase().includes(q) ||
      p.display_name.toLowerCase().includes(q) ||
      p.provider_name.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">{t.pricing.title}</h1>
          <p className="text-xs text-slate-400">
            {t.pricing.subtitle}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <input
              type="text"
              placeholder={t.pricing.searchModels}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="rounded-lg border border-[#1f2433] bg-[#11131c] pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
            <Search className="left-2.5 top-2 absolute h-3.5 w-3.5 text-slate-500" />
          </div>

          <select
            aria-label="Filter pricing by provider"
            value={providerFilter}
            onChange={(e) => setProviderFilter(e.target.value)}
            className="rounded-lg border border-[#1f2433] bg-[#11131c] px-3 py-1.5 text-xs text-slate-200"
          >
            <option value="">{t.pricing.allProviders}</option>
            {(providers || []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          <label className="flex items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={includeHistory}
              onChange={(e) => setIncludeHistory(e.target.checked)}
              className="rounded border-slate-700 bg-slate-900"
            />
            {t.pricing.includeHistory}
          </label>
        </div>
      </div>

      <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
        {isLoading ? (
          <div className="py-8 text-center text-xs text-slate-400">{t.pricing.loadingPricing}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1f2433] text-slate-400">
                  <th className="pb-3 font-medium">{t.pricing.model}</th>
                  <th className="pb-3 font-medium">{t.pricing.provider}</th>
                  <th className="pb-3 font-medium">{t.pricing.contextWindow}</th>
                  <th className="pb-3 font-medium">{t.pricing.inputPer1M}</th>
                  <th className="pb-3 font-medium">{t.pricing.cachedInputPer1M}</th>
                  <th className="pb-3 font-medium">{t.pricing.outputPer1M}</th>
                  <th className="pb-3 font-medium">{t.pricing.currency}</th>
                  <th className="pb-3 font-medium">{t.pricing.source}</th>
                  <th className="pb-3 font-medium">{t.pricing.lastUpdated}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f2433]">
                {filtered.map((item) => (
                  <tr key={item.id} className="hover:bg-[#161a26]">
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <Cpu className="h-3.5 w-3.5 text-indigo-400" />
                        <div>
                          <div className="font-semibold text-white">{item.display_name}</div>
                          <div className="font-mono text-[11px] text-slate-400">
                            {item.model_id}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 text-slate-300">{item.provider_name}</td>
                    <td className="py-3 font-mono text-slate-300">
                      {item.context_window ? `${(item.context_window / 1000).toFixed(0)}K` : '—'}
                    </td>
                    <td className="py-3 font-mono text-cyan-300">
                      ${item.input_price_per_million.toFixed(4)}
                    </td>
                    <td className="py-3 font-mono text-emerald-300">
                      {item.cached_input_price_per_million !== null
                        ? `$${item.cached_input_price_per_million.toFixed(4)}`
                        : '—'}
                    </td>
                    <td className="py-3 font-mono text-violet-300">
                      ${item.output_price_per_million.toFixed(4)}
                    </td>
                    <td className="py-3 font-mono text-slate-300">{item.currency}</td>
                    <td className="py-3">
                      <span className="rounded bg-indigo-500/15 px-2 py-0.5 font-mono text-[10px] text-indigo-300">
                        {item.price_source}
                      </span>
                    </td>
                    <td className="py-3 font-mono text-[11px] text-slate-400">
                      {new Date(item.recorded_at).toISOString().slice(0, 19).replace('T', ' ')}
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
