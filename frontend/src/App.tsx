import React, { useState } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { OverviewPage } from './pages/OverviewPage';
import { ProvidersPage } from './pages/ProvidersPage';
import { UsageAnalyticsPage } from './pages/UsageAnalyticsPage';
import { CreditsBalancePage } from './pages/CreditsBalancePage';
import { ModelPricingPage } from './pages/ModelPricingPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import type { DatePreset } from './types/api';

const defaultQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const AppContent: React.FC = () => {
  const [preset, setPreset] = useState<DatePreset>('30d');
  const [startDate, setStartDate] = useState<string>('2026-10-01');
  const [endDate, setEndDate] = useState<string>('2026-10-31');
  const [currency, setCurrency] = useState<'USD' | 'EUR'>('USD');

  return (
    <Layout
      preset={preset}
      onPresetChange={setPreset}
      startDate={startDate}
      endDate={endDate}
      onStartDateChange={setStartDate}
      onEndDateChange={setEndDate}
      currency={currency}
      onCurrencyChange={setCurrency}
    >
      <Routes>
        <Route
          path="/"
          element={
            <OverviewPage
              preset={preset}
              startDate={startDate}
              endDate={endDate}
              currency={currency}
            />
          }
        />
        <Route path="/providers" element={<ProvidersPage />} />
        <Route
          path="/analytics"
          element={
            <UsageAnalyticsPage
              preset={preset}
              startDate={startDate}
              endDate={endDate}
              currency={currency}
            />
          }
        />
        <Route path="/balances" element={<CreditsBalancePage currency={currency} />} />
        <Route path="/pricing" element={<ModelPricingPage />} />
        <Route
          path="/history"
          element={
            <HistoryPage
              preset={preset}
              startDate={startDate}
              endDate={endDate}
              currency={currency}
            />
          }
        />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
};

export function App() {
  return (
    <QueryClientProvider client={defaultQueryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
