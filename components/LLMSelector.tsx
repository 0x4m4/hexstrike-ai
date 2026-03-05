import { useState } from 'react';
import type { AIProvider, AIProviderConfig, AnalysisMode } from '@/types';
import { PROVIDER_LABELS, PROVIDER_MODELS } from '@/utils/analysisConfig';

interface LLMSelectorProps {
  mode: AnalysisMode;
  onModeChange: (mode: AnalysisMode) => void;
  providers: AIProviderConfig[];
  onProvidersChange: (providers: AIProviderConfig[]) => void;
  apiKeys: Record<AIProvider, string>;
  onApiKeyChange: (provider: AIProvider, key: string) => void;
}

const ALL_PROVIDERS: AIProvider[] = ['gemini', 'openai', 'anthropic', 'lmstudio'];

const MODE_OPTIONS: Array<{ value: AnalysisMode; label: string; description: string }> = [
  { value: 'single', label: 'Single AI', description: 'Fast analysis with one provider' },
  { value: 'board', label: 'Board of Advisors', description: 'Multiple AIs for consensus' },
  { value: 'quick', label: 'Quick Scan', description: 'Rapid top-5 clips' },
];

export function LLMSelector({
  mode,
  onModeChange,
  providers,
  onProvidersChange,
  apiKeys,
  onApiKeyChange,
}: LLMSelectorProps) {
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

  return (
    <div className="glass rounded-xl p-6">
      <h3 className="mb-4 text-lg font-semibold text-text-primary">AI Configuration</h3>

      {/* Mode Selection */}
      <div className="mb-6">
        <label className="mb-2 block text-sm font-medium text-text-secondary">Analysis Mode</label>
        <div className="grid grid-cols-3 gap-2">
          {MODE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onModeChange(opt.value)}
              className={`rounded-lg p-3 text-left transition-all ${
                mode === opt.value
                  ? 'bg-primary text-white'
                  : 'bg-surface text-text-secondary hover:bg-surface-hover'
              }`}
            >
              <div className="text-sm font-medium">{opt.label}</div>
              <div className={`text-xs ${mode === opt.value ? 'text-white/70' : 'text-text-muted'}`}>
                {opt.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Provider Selection */}
      <div>
        <label className="mb-2 block text-sm font-medium text-text-secondary">
          AI Providers {mode === 'board' && '(select multiple)'}
        </label>
        <div className="space-y-2">
          {ALL_PROVIDERS.map((provider) => {
            const isActive = providers.some((p) => p.provider === provider);
            const isExpanded = expandedProvider === provider;
            const hasKey = !!apiKeys[provider];

            return (
              <div key={provider} className="rounded-lg border border-border overflow-hidden">
                <button
                  onClick={() => {
                    toggleProvider(provider);
                    setExpandedProvider(isExpanded ? null : provider);
                  }}
                  className={`flex w-full items-center justify-between p-3 transition-all ${
                    isActive ? 'bg-primary/10' : 'bg-surface hover:bg-surface-hover'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <div
                      className={`h-3 w-3 rounded-full ${
                        isActive && hasKey ? 'bg-green-400' : isActive ? 'bg-yellow-400' : 'bg-gray-400'
                      }`}
                    />
                    <span className="font-medium text-text-primary">
                      {PROVIDER_LABELS[provider]}
                    </span>
                  </div>
                  <span className="text-xs text-text-muted">
                    {isActive ? 'Active' : 'Inactive'}
                  </span>
                </button>

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
                    <div>
                      <label className="mb-1 block text-xs text-text-muted">Model</label>
                      <select
                        value={providers.find((p) => p.provider === provider)?.model}
                        onChange={(e) => updateModel(provider, e.target.value)}
                        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
                      >
                        {PROVIDER_MODELS[provider].map((model) => (
                          <option key={model} value={model}>
                            {model}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
