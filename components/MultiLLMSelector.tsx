import { useState } from 'react';
import type { AIProvider, AIProviderConfig } from '@/types';
import { ModelSelector } from './ModelSelector';
import { PROVIDER_LABELS, PROVIDER_MODELS } from '@/utils/analysisConfig';

interface MultiLLMSelectorProps {
  providers: AIProviderConfig[];
  onProvidersChange: (providers: AIProviderConfig[]) => void;
  apiKeys: Record<AIProvider, string>;
  onApiKeyChange: (provider: AIProvider, key: string) => void;
}

const ALL_PROVIDERS: AIProvider[] = ['gemini', 'openai', 'anthropic', 'lmstudio'];

export function MultiLLMSelector({
  providers,
  onProvidersChange,
  apiKeys,
  onApiKeyChange,
}: MultiLLMSelectorProps) {
  const [expandedProvider, setExpandedProvider] = useState<AIProvider | null>(null);

  const toggleProvider = (provider: AIProvider) => {
    const exists = providers.find((p) => p.provider === provider);
    if (exists) {
      onProvidersChange(providers.filter((p) => p.provider !== provider));
    } else {
      onProvidersChange([
        ...providers,
        {
          provider,
          apiKey: apiKeys[provider] || '',
          model: PROVIDER_MODELS[provider][0],
        },
      ]);
    }
  };

  const updateModel = (provider: AIProvider, model: string) => {
    onProvidersChange(
      providers.map((p) => (p.provider === provider ? { ...p, model } : p))
    );
  };

  const activeCount = providers.length;

  return (
    <div className="glass rounded-xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text-primary">Board of Advisors</h3>
        <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs font-medium text-primary">
          {activeCount} active
        </span>
      </div>

      <p className="mb-4 text-sm text-text-muted">
        Select multiple AI providers for consensus-driven analysis.
        More providers = higher confidence scores.
      </p>

      <div className="space-y-2">
        {ALL_PROVIDERS.map((provider) => {
          const isActive = providers.some((p) => p.provider === provider);
          const isExpanded = expandedProvider === provider;
          const hasKey = !!apiKeys[provider] || provider === 'lmstudio';
          const currentModel = providers.find((p) => p.provider === provider)?.model;

          return (
            <div key={provider} className="rounded-lg border border-border overflow-hidden">
              <div className="flex items-center">
                <button
                  onClick={() => toggleProvider(provider)}
                  className={`flex flex-1 items-center gap-3 p-3 transition-all ${
                    isActive ? 'bg-primary/10' : 'bg-surface hover:bg-surface-hover'
                  }`}
                >
                  <div
                    className={`flex h-5 w-5 items-center justify-center rounded border-2 ${
                      isActive
                        ? 'border-primary bg-primary text-white'
                        : 'border-border'
                    }`}
                  >
                    {isActive && <span className="text-xs">&#10003;</span>}
                  </div>
                  <div className="flex-1 text-left">
                    <div className="text-sm font-medium text-text-primary">
                      {PROVIDER_LABELS[provider]}
                    </div>
                    {isActive && currentModel && (
                      <div className="text-xs text-text-muted">{currentModel}</div>
                    )}
                  </div>
                  <div
                    className={`h-2 w-2 rounded-full ${
                      isActive && hasKey ? 'bg-green-400' : isActive ? 'bg-yellow-400' : 'bg-gray-400'
                    }`}
                  />
                </button>
                {isActive && (
                  <button
                    onClick={() => setExpandedProvider(isExpanded ? null : provider)}
                    className="px-3 py-3 text-xs text-text-muted hover:text-text-primary"
                  >
                    {isExpanded ? '▲' : '▼'}
                  </button>
                )}
              </div>

              {isActive && isExpanded && (
                <div className="border-t border-border bg-surface p-3 space-y-3">
                  {provider !== 'lmstudio' && (
                    <div>
                      <label className="mb-1 block text-xs text-text-muted">API Key</label>
                      <input
                        type="password"
                        value={apiKeys[provider]}
                        onChange={(e) => onApiKeyChange(provider, e.target.value)}
                        placeholder={`Enter ${PROVIDER_LABELS[provider]} API key`}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
                      />
                    </div>
                  )}
                  <ModelSelector
                    provider={provider}
                    value={currentModel || PROVIDER_MODELS[provider][0]}
                    onChange={(model) => updateModel(provider, model)}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
