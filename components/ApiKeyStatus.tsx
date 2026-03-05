import { useState, useEffect } from 'react';
import type { AIProvider, ProviderStatus } from '@/types';
import { PROVIDER_LABELS } from '@/utils/analysisConfig';

interface ApiKeyStatusProps {
  apiKeys: Record<AIProvider, string>;
  providers?: AIProvider[];
}

export function ApiKeyStatus({ apiKeys, providers }: ApiKeyStatusProps) {
  const [statuses, setStatuses] = useState<ProviderStatus[]>([]);

  const providersToCheck = providers || (['gemini', 'openai', 'anthropic', 'lmstudio'] as AIProvider[]);

  useEffect(() => {
    const newStatuses: ProviderStatus[] = providersToCheck.map((provider) => ({
      provider,
      isConfigured: provider === 'lmstudio' || !!apiKeys[provider],
      isAvailable: provider === 'lmstudio' || apiKeys[provider]?.length > 10,
      lastChecked: new Date(),
    }));
    setStatuses(newStatuses);
  }, [apiKeys, providersToCheck.join(',')]);

  return (
    <div className="flex flex-wrap gap-2">
      {statuses.map((status) => (
        <div
          key={status.provider}
          className="flex items-center gap-1.5 rounded-full bg-surface px-3 py-1"
          title={`${PROVIDER_LABELS[status.provider]}: ${
            status.isAvailable ? 'Ready' : status.isConfigured ? 'Key may be invalid' : 'Not configured'
          }`}
        >
          <div
            className={`h-2 w-2 rounded-full ${
              status.isAvailable
                ? 'bg-green-400'
                : status.isConfigured
                ? 'bg-yellow-400'
                : 'bg-gray-400'
            }`}
          />
          <span className="text-xs text-text-muted">
            {PROVIDER_LABELS[status.provider]}
          </span>
        </div>
      ))}
    </div>
  );
}
