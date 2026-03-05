import React from 'react';
import { Header } from './Header';
import { ToastProvider } from './ToastProvider';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-background text-text-primary transition-theme">
        <Header />
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </ToastProvider>
  );
}
