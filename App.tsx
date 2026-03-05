import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@/components/ThemeProvider';
import { Layout } from '@/components/Layout';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { PageLoader } from '@/components/Loader';
import { useAuth } from '@/hooks/useAuth';

// Lazy-loaded pages
const LandingPage = React.lazy(() => import('./pages/LandingPage').then((m) => ({ default: m.LandingPage })));
const AboutPage = React.lazy(() => import('./pages/AboutPage').then((m) => ({ default: m.AboutPage })));
const PricingPage = React.lazy(() => import('./pages/PricingPage').then((m) => ({ default: m.PricingPage })));
const Dashboard = React.lazy(() => import('./pages/Dashboard').then((m) => ({ default: m.Dashboard })));
const ProjectsPage = React.lazy(() => import('./pages/ProjectsPage').then((m) => ({ default: m.ProjectsPage })));
const ProjectCreatePage = React.lazy(() => import('./pages/ProjectCreatePage').then((m) => ({ default: m.ProjectCreatePage })));
const ProjectDetailPage = React.lazy(() => import('./pages/ProjectDetailPage').then((m) => ({ default: m.ProjectDetailPage })));
const QuickAnalyzePage = React.lazy(() => import('./pages/QuickAnalyzePage').then((m) => ({ default: m.QuickAnalyzePage })));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const HistoryPage = React.lazy(() => import('./pages/HistoryPage').then((m) => ({ default: m.HistoryPage })));
const AllClipsPage = React.lazy(() => import('./pages/AllClipsPage').then((m) => ({ default: m.AllClipsPage })));
const TrimClipsPage = React.lazy(() => import('./pages/TrimClipsPage').then((m) => ({ default: m.TrimClipsPage })));
const ExportPage = React.lazy(() => import('./pages/ExportPage').then((m) => ({ default: m.ExportPage })));
const AnalyticsPage = React.lazy(() => import('./pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <PageLoader />;
  if (!isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <PageLoader />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <BrowserRouter>
          <Layout>
            <Suspense fallback={<PageLoader />}>
              <Routes>
                {/* Public routes */}
                <Route path="/" element={<PublicRoute><LandingPage /></PublicRoute>} />
                <Route path="/about" element={<AboutPage />} />
                <Route path="/pricing" element={<PricingPage />} />

                {/* Protected routes */}
                <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/projects" element={<ProtectedRoute><ProjectsPage /></ProtectedRoute>} />
                <Route path="/projects/new" element={<ProtectedRoute><ProjectCreatePage /></ProtectedRoute>} />
                <Route path="/projects/:id" element={<ProtectedRoute><ProjectDetailPage /></ProtectedRoute>} />
                <Route path="/quick-analyze" element={<ProtectedRoute><QuickAnalyzePage /></ProtectedRoute>} />
                <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
                <Route path="/history" element={<ProtectedRoute><HistoryPage /></ProtectedRoute>} />
                <Route path="/clips" element={<ProtectedRoute><AllClipsPage /></ProtectedRoute>} />
                <Route path="/trim" element={<ProtectedRoute><TrimClipsPage /></ProtectedRoute>} />
                <Route path="/export" element={<ProtectedRoute><ExportPage /></ProtectedRoute>} />
                <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </Layout>
        </BrowserRouter>
      </ErrorBoundary>
    </ThemeProvider>
  );
}
