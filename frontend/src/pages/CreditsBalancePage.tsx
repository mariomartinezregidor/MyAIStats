import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, HelpCircle, Wallet } from 'lucide-react';
import { api, formatMoney } from '../api/client';
import { useI18n } from '../i18n';

interface CreditsBalancePageProps {
  currency: 'USD' | 'EUR';
}

export const CreditsBalancePage: React.FC<CreditsBalancePageProps> = ({ currency }) => {
  const { t } = useI18n();
  const { data: balances, isLoading } = useQuery({
    queryKey: ['balances', currency],
    queryFn: () => api.getBalances(currency),
  });

  if (isLoading || !balances) {
    return (
      <div className="py-12 text-center text-xs text-slate-400">
        Loading confirmed account balances...
      </div>
    );
  }

  const supported = balances.filter((b) => b.is_supported);
  const unsupported = balances.filter((b) => !b.is_supported);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">
          {t.balances.title}
        </h1>
        <p className="text-xs text-slate-400">
          {t.balances.subtitle}
        </p>
      </div>

      {/* Confirmed Balances Section */}
      <div className="space-y-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
          <CheckCircle2 className="h-4 w-4" />
          {t.balances.confirmedBalances}
        </h2>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {supported.map((item) => (
            <div
              key={item.account_id}
              className="rounded-xl border border-[#1f2433] bg-[#11131c] p-5"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">{item.account_name}</span>
                    {item.is_demo && (
                      <span className="rounded bg-amber-500/20 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-amber-300">
                        DEMO
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-indigo-300">{item.provider_name}</span>
                </div>
                <Wallet className="h-5 w-5 text-emerald-400" />
              </div>

              <div className="mt-4 flex items-baseline gap-3">
                <span className="text-3xl font-bold text-emerald-400">
                  {formatMoney(item.converted_available_balance, item.display_currency)}
                </span>
                {item.original_currency !== item.display_currency &&
                  item.available_balance !== null && (
                    <span className="font-mono text-xs text-slate-400">
                      (Original: {formatMoney(item.available_balance, item.original_currency)})
                    </span>
                  )}
              </div>

              {item.is_low_balance && (
                <div className="mt-3 flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-300">
                  <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                  <span>
                    {t.balances.lowBalanceAlert}{' '}
                    {formatMoney(item.low_balance_threshold, item.original_currency)}
                  </span>
                </div>
              )}

              <div className="mt-4 grid grid-cols-2 gap-2 border-t border-[#1f2433] pt-3 text-xs text-slate-400">
                <div>
                  {t.balances.totalCredits}{' '}
                  <span className="font-mono text-slate-200">
                    {formatMoney(item.total_credits, item.original_currency)}
                  </span>
                </div>
                <div>
                  {t.balances.usedCredits}{' '}
                  <span className="font-mono text-slate-200">
                    {formatMoney(item.used_credits, item.original_currency)}
                  </span>
                </div>
              </div>
              {item.status_note && (
                <p className="mt-2 text-[11px] text-slate-400">{item.status_note}</p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Unsupported Balances Section */}
      <div className="space-y-3">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-300">
          <HelpCircle className="h-4 w-4 text-slate-400" />
          {t.balances.unsupportedProviders}
        </h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {unsupported.map((item) => (
            <div
              key={item.account_id}
              className="rounded-xl border border-[#1f2433] bg-[#0c0e16] p-5 opacity-90"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-semibold text-slate-200">
                    {item.account_name}
                  </span>
                  <div className="text-xs text-slate-400">{item.provider_name}</div>
                </div>
                <span className="rounded-full border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-[11px] font-medium text-slate-300">
                  {t.balances.balanceApiUnsupported}
                </span>
              </div>
              <p className="mt-3 text-xs text-slate-400">{item.status_note}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
