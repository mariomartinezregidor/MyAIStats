import React from 'react';
import { Calendar, Coins } from 'lucide-react';
import type { DatePreset } from '../types/api';

interface FilterBarProps {
  preset: DatePreset;
  onPresetChange: (p: DatePreset) => void;
  startDate: string;
  endDate: string;
  onStartDateChange: (v: string) => void;
  onEndDateChange: (v: string) => void;
  currency: 'USD' | 'EUR';
  onCurrencyChange: (c: 'USD' | 'EUR') => void;
}

const PRESETS: { id: DatePreset; label: string }[] = [
  { id: 'today', label: 'Today' },
  { id: '7d', label: 'Last 7 days' },
  { id: '30d', label: 'Last 30 days' },
  { id: 'current_month', label: 'Current month' },
  { id: 'previous_month', label: 'Previous month' },
  { id: 'custom', label: 'Custom range' },
];

export const FilterBar: React.FC<FilterBarProps> = ({
  preset,
  onPresetChange,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  currency,
  onCurrencyChange,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#1f2433] bg-[#11131c]/90 px-4 py-2.5 backdrop-blur">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="mr-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-400">
          <Calendar className="h-3.5 w-3.5 text-indigo-400" />
          Period:
        </span>
        {PRESETS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => onPresetChange(p.id)}
            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition-colors ${
              preset === p.id
                ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/20'
                : 'text-slate-400 hover:bg-[#181b28] hover:text-slate-200'
            }`}
          >
            {p.label}
          </button>
        ))}

        {preset === 'custom' && (
          <div className="ml-2 flex items-center gap-2">
            <input
              type="date"
              aria-label="Start date"
              value={startDate}
              onChange={(e) => onStartDateChange(e.target.value)}
              className="rounded-md border border-[#1f2433] bg-[#090a0f] px-2 py-1 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
            <span className="text-xs text-slate-500">to</span>
            <input
              type="date"
              aria-label="End date"
              value={endDate}
              onChange={(e) => onEndDateChange(e.target.value)}
              className="rounded-md border border-[#1f2433] bg-[#090a0f] px-2 py-1 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        <span className="flex items-center gap-1 text-xs text-slate-400">
          <Coins className="h-3.5 w-3.5 text-emerald-400" />
          Currency:
        </span>
        <div className="inline-flex rounded-lg border border-[#1f2433] bg-[#090a0f] p-0.5">
          {(['USD', 'EUR'] as const).map((cur) => (
            <button
              key={cur}
              type="button"
              onClick={() => onCurrencyChange(cur)}
              className={`rounded-md px-2.5 py-1 text-xs font-semibold transition ${
                currency === cur
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {cur}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
