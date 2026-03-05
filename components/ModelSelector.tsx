import type { AIProvider } from '@/types';
import { PROVIDER_MODELS, PROVIDER_LABELS } from '@/utils/analysisConfig';

interface ModelSelectorProps {
  provider: AIProvider;
  value: string;
  onChange: (model: string) => void;
  disabled?: boolean;
}

export function ModelSelector({ provider, value, onChange, disabled }: ModelSelectorProps) {
  const models = PROVIDER_MODELS[provider];

  return (
    <div>
      <label className="mb-1 block text-xs text-text-muted">
        {PROVIDER_LABELS[provider]} Model
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none disabled:opacity-50"
      >
        {models.map((model) => (
          <option key={model} value={model}>
            {model}
          </option>
        ))}
      </select>
    </div>
  );
}
