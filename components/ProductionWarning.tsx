import { useState } from 'react';

export function ProductionWarning() {
  const [dismissed, setDismissed] = useState(false);

  const isPlaceholderConfig =
    import.meta.env.VITE_FIREBASE_API_KEY === 'your-api-key' ||
    !import.meta.env.VITE_FIREBASE_API_KEY;

  if (!isPlaceholderConfig || dismissed) return null;

  return (
    <div className="border-b border-yellow-500/30 bg-yellow-500/10 px-4 py-2">
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <p className="text-sm text-yellow-400">
          <span className="font-medium">Development Mode:</span> Firebase is not configured.
          Copy <code className="rounded bg-yellow-500/20 px-1">.env.development</code> to{' '}
          <code className="rounded bg-yellow-500/20 px-1">.env.local</code> and add your credentials.
        </p>
        <button
          onClick={() => setDismissed(true)}
          className="ml-4 text-sm text-yellow-400 hover:text-yellow-300"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
