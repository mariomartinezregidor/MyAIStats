import React, { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Database, Download, Save, ShieldCheck, Upload } from 'lucide-react';
import { api } from '../api/client';
import { useI18n } from '../i18n';

export const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { t, lang, setLang } = useI18n();
  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  });

  const [defaultCurrency, setDefaultCurrency] = useState<'USD' | 'EUR'>('USD');
  const [demoMode, setDemoMode] = useState(true);
  const [usageInt, setUsageInt] = useState(15);
  const [costsInt, setCostsInt] = useState(30);
  const [balancesInt, setBalancesInt] = useState(30);
  const [pricingInt, setPricingInt] = useState(1440);
  const [usdToEur, setUsdToEur] = useState(0.92);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setDefaultCurrency(settings.default_currency);
      setDemoMode(settings.demo_mode);
      setUsageInt(settings.sync_usage_interval_minutes);
      setCostsInt(settings.sync_costs_interval_minutes);
      setBalancesInt(settings.sync_balances_interval_minutes);
      setPricingInt(settings.sync_pricing_interval_minutes);
      setUsdToEur(settings.usd_to_eur_rate);
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: api.updateSettings,
    onSuccess: () => {
      setStatusMsg(t.settings.settingsSaved);
      queryClient.invalidateQueries();
    },
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate({
      default_currency: defaultCurrency,
      demo_mode: demoMode,
      sync_usage_interval_minutes: Number(usageInt),
      sync_costs_interval_minutes: Number(costsInt),
      sync_balances_interval_minutes: Number(balancesInt),
      sync_pricing_interval_minutes: Number(pricingInt),
      usd_to_eur_rate: Number(usdToEur),
    });
  };

  const handleRestoreFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/restore', {
      method: 'POST',
      body: formData,
    });
    if (res.ok) {
      setStatusMsg(t.settings.restored);
      queryClient.invalidateQueries();
    } else {
      setStatusMsg(t.settings.restoreFailed);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          {t.settings.title}
        </h1>
        <p className="text-xs text-slate-400">
          {t.settings.subtitle}
        </p>
      </div>

      {statusMsg && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-200">
          {statusMsg}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Synchronization & Currency Settings */}
        <form
          onSubmit={handleSave}
          className="space-y-4 rounded-xl border border-[#1f2433] bg-[#11131c] p-5"
        >
          <h2 className="text-sm font-semibold text-white">
            {t.settings.syncCurrencyConfig}
          </h2>

          <div>
            <label className="block text-xs font-medium text-slate-300">
              {t.language}
            </label>
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value as 'en' | 'es')}
              className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs text-slate-100"
            >
              <option value="en">{t.english}</option>
              <option value="es">{t.spanish}</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.settings.defaultCurrency}
              </label>
              <select
                value={defaultCurrency}
                onChange={(e) => setDefaultCurrency(e.target.value as 'USD' | 'EUR')}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 text-xs text-slate-100"
              >
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.settings.storedRate}
              </label>
              <input
                type="number"
                step="0.0001"
                value={usdToEur}
                onChange={(e) => setUsdToEur(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 font-mono text-xs text-slate-100"
              />
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-[#1f2433] bg-[#0c0e16] p-3">
            <div>
              <div className="text-xs font-semibold text-white">{t.settings.demoMode}</div>
              <div className="text-[11px] text-slate-400">
                {t.settings.demoModeDesc}
              </div>
            </div>
            <input
              type="checkbox"
              aria-label="Enable Demo Mode"
              checked={demoMode}
              onChange={(e) => setDemoMode(e.target.checked)}
              className="h-4 w-4 rounded border-slate-700 bg-slate-900"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.settings.usageSyncInterval}
              </label>
              <input
                type="number"
                min={1}
                value={usageInt}
                onChange={(e) => setUsageInt(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 font-mono text-xs text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.settings.costsSyncInterval}
              </label>
              <input
                type="number"
                min={1}
                value={costsInt}
                onChange={(e) => setCostsInt(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 font-mono text-xs text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.settings.balancesSyncInterval}
              </label>
              <input
                type="number"
                min={1}
                value={balancesInt}
                onChange={(e) => setBalancesInt(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 font-mono text-xs text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300">
                {t.settings.pricingSyncInterval}
              </label>
              <input
                type="number"
                min={15}
                value={pricingInt}
                onChange={(e) => setPricingInt(Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-[#1f2433] bg-[#090a0f] px-3 py-2 font-mono text-xs text-slate-100"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-500"
          >
            <Save className="h-3.5 w-3.5" />
            {t.settings.saveConfig}
          </button>
        </form>

        {/* Exports, Backup & Security Architecture */}
        <div className="space-y-6">
          <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-white">
                {t.settings.exportsBackup}
              </h2>
            </div>
            <p className="mt-1 text-xs text-slate-400">
              {t.settings.exportsBackupDesc}
            </p>

            <div className="mt-4 flex flex-wrap gap-2">
              <a
                href="/api/export/csv?dataset=usage"
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#1f2433] bg-[#0c0e16] px-3 py-2 text-xs font-medium text-slate-200 hover:border-indigo-500/40"
              >
                <Download className="h-3.5 w-3.5 text-cyan-400" />
                Usage (CSV)
              </a>
              <a
                href="/api/export/json?dataset=costs"
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#1f2433] bg-[#0c0e16] px-3 py-2 text-xs font-medium text-slate-200 hover:border-indigo-500/40"
              >
                <Download className="h-3.5 w-3.5 text-emerald-400" />
                Costs (JSON)
              </a>
              <a
                href="/api/export/json?dataset=balances"
                className="inline-flex items-center gap-1.5 rounded-lg border border-[#1f2433] bg-[#0c0e16] px-3 py-2 text-xs font-medium text-slate-200 hover:border-indigo-500/40"
              >
                <Download className="h-3.5 w-3.5 text-amber-400" />
                Balances (JSON)
              </a>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-[#1f2433] pt-4">
              <a
                href="/api/backup"
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600/20 border border-emerald-500/30 px-3.5 py-2 text-xs font-semibold text-emerald-200 hover:bg-emerald-600/30"
              >
                <Download className="h-3.5 w-3.5" />
                {t.settings.downloadBackup}
              </a>

              <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-[#1f2433] bg-[#0c0e16] px-3.5 py-2 text-xs font-medium text-slate-200 hover:border-indigo-500/40">
                <Upload className="h-3.5 w-3.5 text-indigo-400" />
                <span>{t.settings.restoreBackup}</span>
                <input
                  type="file"
                  accept=".db,.sqlite,.sqlite3"
                  onChange={handleRestoreFile}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          <div className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-white">
                {t.settings.localFirstSecurity}
              </h2>
            </div>
            <ul className="mt-3 space-y-2 text-xs text-slate-400">
              <li>
                • <strong className="text-slate-200">{t.settings.localhostBinding}</strong> {t.settings.localhostBindingDesc}
              </li>
              <li>
                • <strong className="text-slate-200">{t.settings.fernetVault}</strong> {t.settings.fernetVaultDesc}
              </li>
              <li>
                • <strong className="text-slate-200">{t.settings.ssrfAllowlist}</strong> {t.settings.ssrfAllowlistDesc}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
