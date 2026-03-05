import type { AnalysisProgress } from '@/types';

interface LoaderProps {
  progress?: AnalysisProgress;
  message?: string;
}

export function Loader({ progress, message }: LoaderProps) {
  const displayMessage = progress?.message || message || 'Loading...';
  const percent = progress?.progress ?? 0;

  return (
    <div className="flex flex-col items-center justify-center py-12">
      {/* Spinner */}
      <div className="relative mb-6">
        <div className="h-16 w-16 rounded-full border-4 border-surface" />
        <div
          className="absolute inset-0 h-16 w-16 animate-spin rounded-full border-4 border-transparent border-t-primary"
          style={{ animationDuration: '1s' }}
        />
        {percent > 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-bold text-primary">{percent}%</span>
          </div>
        )}
      </div>

      <p className="mb-2 text-text-primary font-medium">{displayMessage}</p>

      {progress && (
        <div className="w-full max-w-xs">
          <div className="h-2 rounded-full bg-surface overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${percent}%` }}
            />
          </div>
          {progress.provider && (
            <p className="mt-2 text-center text-xs text-text-muted">
              Provider: {progress.provider}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <Loader message="Loading page..." />
    </div>
  );
}
