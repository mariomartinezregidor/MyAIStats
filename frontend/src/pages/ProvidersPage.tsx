import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle2,
  ExternalLink,
  KeyRound,
  Plus,
  RefreshCw,
  ShieldAlert,
  Trash2,
  XCircle,
} from 'lucide-react';
import { api } from '../api/client';
import { useI18n } from '../i18n';

export const ProvidersPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const [providerId, setProviderId] = useState('openai');
  const [name, setName] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [orgId, setOrgId] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  const [threshold, setThreshold] = useState('');
  const [feedback, setFeedback] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const { data: providers } = useQuery({
    queryKey: ['providers'],
    queryFn: api.getProviders,
  });

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.getAccounts(true),
  });

  const connectMutation = useMutation({
    mutationFn: api.connectAccount,
    onSuccess: (created) => {
      setName('');
      setApiKey('');
      setOrgId('');
      setWorkspaceId('');
      setThreshold('');
      setFeedback({
        type: 'ok',
        text: `Connected "${created.name}" (${created.status_message || created.status}). API key encrypted at rest.`,
      });
      queryClient.invalidateQueries();
    },
    onError: (err: Error) => {
      setFeedback({ type: 'err', text: err.message });
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: number) => api.testAccount(id),
    onSuccess: (res) => {
      setFeedback({
        type: res.success ? 'ok' : 'err',
        text: `${res.message}${res.warnings.length ? ' — ' + res.warnings.join(' ') : ''}`,
      });
      queryClient.invalidateQueries();
    },
  });

  const syncMutation = useMutation({
    mutationFn: (id: number) => api.syncAccount(id),
    onSuccess: (job) => {
      setFeedback({
        type: job.status === 'failed' ? 'err' : 'ok',
        text: job.message || `Sync finished (${job.records_synced} records).`,
      });
      queryClient.invalidateQueries();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteAccount(id),
    onSuccess: () => {
      setFeedback({ type: 'ok', text: 'Account and encrypted credentials removed.' });
      queryClient.invalidateQueries();
    },
  });

  const selectedProvider = providers?.find((p) => p.id === providerId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !apiKey.trim()) return;
    connectMutation.mutate({
      provider_id: providerId,
      name: name.trim(),
      api_key: apiKey.trim(),
      organization_id: orgId.trim() || undefined,
      workspace_id: workspaceId.trim() || undefined,
      low_balance_threshold: threshold ? Number(threshold) : null,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          {t.providers.title}
        </h1>
        <p className="text-xs text-slate-400">
          {t.providers.subtitle}
        </p>
      </div>

      {feedback && (
        <div
          className={`rounded-xl border px-4 py-3 text-xs ${
            feedback.type === 'ok'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200'
              : 'border-rose-500/30 bg-rose-500/10 text-rose-200'
          }`}
        >
          {feedback.text}
        </div>
      )}

      {/* Connect New Account Form */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-xl border border-[#1f2433] bg-[#11131c] p-5 lg:col-span-1"
        >
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-white">{t.providers.connectAccount}</h2>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">{t.providers.provider}</label>
            <select
              aria-label="Provider"
              value={providerId}
              onChange={(e) => setProviderId(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:outline-none"
            >
              {(providers || []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} (Priority {p.category_priority})
                </option>
              ))}
            </select>
          </div>

          {selectedProvider && (
            <div className="rounded-lg border border-indigo-500/20 bg-indigo-500/5 p-3 text-[11px] text-slate-300">
              <div className="font-semibold text-indigo-300">
                Official API Permissions & Capabilities:
              </div>
              <p className="mt-1 leading-relaxed text-slate-400">
                {selectedProvider.auth_instructions}
              </p>
              <a
                href={selectedProvider.docs_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-indigo-400 hover:underline"
              >
                {t.providers.docsLink} <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300">
              {t.providers.accountLabel}
            </label>
            <input
              type="text"
              required
              placeholder={t.providers.accountLabelPlaceholder}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300">{t.providers.apiKey}</label>
            <div className="relative mt-1">
              <input
                type="password"
                required
                autoComplete="off"
                placeholder="sk-... / gsk_... / fw_..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs font-mono text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
              <KeyRound className=" right-3 top-2.5 absolute h-3.5 w-3.5 text-slate-500" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.providers.orgId}
              </label>
              <input
                type="text"
                placeholder="org-..."
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300">
                Workspace ID (Anthropic service accounts)
              </label>
              <input
                type="text"
                placeholder="wrkspc_..."
                value={workspaceId}
                onChange={(e) => setWorkspaceId(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.providers.lowBalanceAlert}
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g. 15.00"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs text-slate-100 focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={connectMutation.isPending}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:opacity-50"
          >
            {connectMutation.isPending ? t.providers.connecting : t.providers.connectBtn}
          </button>
        </form>

        {/* Connected Accounts Table */}
        <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5 lg:col-span-2">
          <h2 className="text-sm font-semibold text-white">{t.providers.connectedAccounts}</h2>
          <p className="mb-4 text-xs text-slate-400">
            {t.providers.connectedAccountsDesc}
          </p>

          <div className="space-y-3">
            {(accounts || []).map((acc) => (
              <div
                key={acc.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#1f2433] bg-[#0c0e16] p-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{acc.name}</span>
                    <span className="rounded bg-[#181b28] px-2 py-0.5 text-[11px] font-medium text-indigo-300">
                      {acc.provider_name}
                    </span>
                    {acc.is_demo && (
                      <span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-amber-300">
                        DEMO
                      </span>
                    )}
                    {acc.is_admin_key && (
                      <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">
                        Admin / Billing Scope
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400">
                    {t.providers.keyHint} <span className="font-mono text-slate-300">{acc.masked_key_hint}</span>
                    {acc.last_sync_at && (
                      <span className="ml-3">
                        • {t.providers.lastSynced} {new Date(acc.last_sync_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  {acc.status_message && (
                    <p className="text-[11px] text-slate-400">{acc.status_message}</p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => testMutation.mutate(acc.id)}
                    className="rounded-lg border border-[#1f2433] bg-[#141824] px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-indigo-500/40"
                  >
                    {t.providers.testConnection}
                  </button>
                  <button
                    type="button"
                    onClick={() => syncMutation.mutate(acc.id)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/30 bg-indigo-600/20 px-3 py-1.5 text-xs font-medium text-indigo-200 hover:bg-indigo-600/30"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    {t.providers.sync}
                  </button>
                  {!acc.is_demo && (
                    <button
                      type="button"
                      onClick={() => deleteMutation.mutate(acc.id)}
                      className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-1.5 text-rose-300 hover:bg-rose-500/20"
                      title="Delete account"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Official Provider Capability Matrix */}
      <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
        <h2 className="text-sm font-semibold text-white">
          Verified Official Provider Capability Matrix
        </h2>
        <p className="mb-4 text-xs text-slate-400">
          {t.providers.officialCapabilityMatrixDesc}
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#1f2433] text-slate-400">
                <th className="pb-3 font-medium">Provider</th>
                <th className="pb-3 font-medium">{t.providers.priority}</th>
                <th className="pb-3 font-medium">{t.providers.connectionTest}</th>
                <th className="pb-3 font-medium">{t.providers.tokenUsageApi}</th>
                <th className="pb-3 font-medium">{t.providers.officialCostsApi}</th>
                <th className="pb-3 font-medium">{t.providers.confirmedBalanceApi}</th>
                <th className="pb-3 font-medium">{t.providers.modelPricing}</th>
                <th className="pb-3 font-medium">{t.providers.verificationNotes}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f2433]">
              {(providers || []).map((p) => (
                <tr key={p.id} className="hover:bg-[#161a26]">
                  <td className="py-3 font-semibold text-white">{p.name}</td>
                  <td className="py-3">
                    <span className="rounded bg-indigo-500/15 px-2 py-0.5 font-mono text-[10px] text-indigo-300">
                      P{p.category_priority}
                    </span>
                  </td>
                  <td className="py-3">
                    <Badge supported={p.supports_connection_test} />
                  </td>
                  <td className="py-3">
                    <Badge
                      supported={p.supports_usage}
                      adminRequired={p.requires_admin_key_for_usage}
                    />
                  </td>
                  <td className="py-3">
                    <Badge
                      supported={p.supports_costs}
                      adminRequired={p.requires_admin_key_for_usage}
                    />
                  </td>
                  <td className="py-3">
                    <Badge supported={p.supports_balance} />
                  </td>
                  <td className="py-3">
                    <Badge supported={p.supports_pricing} />
                  </td>
                  <td className="max-w-md py-3 text-[11px] text-slate-400">
                    {p.capability_notes}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

const Badge: React.FC<{ supported: boolean; adminRequired?: boolean }> = ({
  supported,
  adminRequired,
}) => {
  if (!supported) {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
        <XCircle className="h-3 w-3 text-slate-500" />
        Unsupported
      </span>
    );
  }
  if (adminRequired) {
    return (
      <span className="inline-flex items-center gap-1 rounded bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300">
        <ShieldAlert className="h-3 w-3 text-amber-400" />
        Admin Key
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded bg-emerald-500/15 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
      <CheckCircle2 className="h-3 w-3 text-emerald-400" />
      Supported
    </span>
  );
};
