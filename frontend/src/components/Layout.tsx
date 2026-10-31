import React from 'react';
import { NavLink } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  BarChart3,
  Clock,
  Cpu,
  LayoutDashboard,
  RefreshCw,
  Server,
  Settings,
  ShieldCheck,
  Sparkles,
  Wallet,
} from 'lucide-react';
import { api } from '../api/client';
import { FilterBar } from './FilterBar';
import type { DatePreset } from '../types/api';

interface LayoutProps {
  children: React.ReactNode;
  preset: DatePreset;
  onPresetChange: (p: DatePreset) => void;
  startDate: string;
  endDate: string;
  onStartDateChange: (v: string) => void;
  onEndDateChange: (v: string) => void;
  currency: 'USD' | 'EUR';
  onCurrencyChange: (c: 'USD' | 'EUR') => void;
}

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/providers', label: 'Providers', icon: Server },
  { to: '/analytics', label: 'Usage Analytics', icon: BarChart3 },
  { to: '/balances', label: 'Credits & Balance', icon: Wallet },
  { to: '/pricing', label: 'Model Pricing', icon: Cpu },
  { to: '/history', label: 'History', icon: Clock },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export const Layout: React.FC<LayoutProps> = ({
  children,
  preset,
  onPresetChange,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  currency,
  onCurrencyChange,
}) => {
  const queryClient = useQueryClient();

  const { data: syncStatus } = useQuery({
    queryKey: ['syncStatus'],
    queryFn: api.getSyncStatus,
    refetchInterval: 15000,
  });

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettings,
  });

  const syncMutation = useMutation({
    mutationFn: () => api.runGlobalSync('full'),
    onSuccess: () => {
      queryClient.invalidateQueries();
    },
  });

  return (
    <div className="flex min-h-screen bg-[#090a0f] text-slate-100">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-[#1f2433] bg-[#0c0e16]">
        <div className="flex items-center gap-3 border-b border-[#1f2433] px-5 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
            <Activity className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-bold tracking-tight text-white">
                MyAIStats
              </span>
              <span className="rounded bg-indigo-500/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-indigo-400">
                v0.1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              All your AI usage. One dashboard.
            </p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-400 hover:bg-[#141824] hover:text-slate-200 border border-transparent'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Local-first security & sync footer */}
        <div className="space-y-3 border-t border-[#1f2433] p-4">
          {settings?.demo_mode && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-300">
              <div className="flex items-center gap-1.5 font-semibold">
                <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                <span>Demo Mode Active</span>
              </div>
              <p className="mt-1 text-[11px] text-amber-200/80">
                Simulated records are labeled <span className="font-mono">[DEMO]</span>. Disable anytime in Settings.
              </p>
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
              Local-First Vault
            </span>
            <span className="font-mono text-[11px] text-slate-500">127.0.0.1</span>
          </div>

          <button
            type="button"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || syncStatus?.is_running}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-indigo-500/30 bg-indigo-600/20 px-3 py-2 text-xs font-semibold text-indigo-200 transition hover:bg-indigo-600/30 disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${
                syncMutation.isPending || syncStatus?.is_running ? 'animate-spin' : ''
              }`}
            />
            {syncMutation.isPending || syncStatus?.is_running
              ? 'Synchronizing...'
              : 'Sync All Accounts'}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex flex-1 flex-col pl-64">
        <header className="sticky top-0 z-20 border-b border-[#1f2433] bg-[#090a0f]/80 px-6 py-3 backdrop-blur">
          <FilterBar
            preset={preset}
            onPresetChange={onPresetChange}
            startDate={startDate}
            endDate={endDate}
            onStartDateChange={onStartDateChange}
            onEndDateChange={onEndDateChange}
            currency={currency}
            onCurrencyChange={onCurrencyChange}
          />
        </header>

        <main className="flex-1 px-6 py-6">{children}</main>
      </div>
    </div>
  );
};
