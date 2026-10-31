import React, { useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { I18nProvider } from './i18n';
import { AuthProvider, useAuth } from './auth/AuthContext';
import { Layout } from './components/Layout';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { ProvidersPage } from './pages/ProvidersPage';
import { UsageAnalyticsPage } from './pages/UsageAnalyticsPage';
import { CreditsBalancePage } from './pages/CreditsBalancePage';
import { ModelPricingPage } from './pages/ModelPricingPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { UsersPage } from './pages/UsersPage';
import type { DatePreset } from './types/api';

const defaultQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const Protected: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#090a0f] text-slate-300">
        Loading...
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

export const AppContent: React.FC = () => {
  const [preset, setPreset] = useState<DatePreset>('30d');
  const [startDate, setStartDate] = useState<string>('2026-10-01');
  const [endDate, setEndDate] = useState<string>('2026-10-31');
  const [currency, setCurrency] = useState<'USD' | 'EUR'>('USD');

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <Protected>
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
                <Route path="/users" element={<UsersPage />} />
              </Routes>
            </Layout>
          </Protected>
        }
      />
    </Routes>
  );
};

export function App() {
  return (
    <QueryClientProvider client={defaultQueryClient}>
      <I18nProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </AuthProvider>
      </I18nProvider>
    </QueryClientProvider>
  );
}

export default App;