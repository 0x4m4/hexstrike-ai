import { useState } from 'react';
import { VideoInput } from '@/components/VideoInput';
import { ClipCard } from '@/components/ClipCard';
import { Loader } from '@/components/Loader';
import { quickAnalyze } from '@/services/quickAnalysisService';
import { createProviderConfig } from '@/utils/analysisConfig';
import type { AIProvider, Clip, QuickAnalysisResult, VideoInputSource } from '@/types';

export function QuickAnalyzePage() {
  const [apiKey, setApiKey] = useState('');
  const [provider, setProvider] = useState<AIProvider>('gemini');
  const [result, setResult] = useState<QuickAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (source: VideoInputSource) => {
    if (!apiKey && provider !== 'lmstudio') {
      setError('Please enter an API key');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const config = createProviderConfig(provider, apiKey);
      const analysis = await quickAnalyze(source, config);
      setResult(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Quick Analyze</h1>
        <p className="text-text-secondary">
          Fast analysis that returns the top 5 most viral clips
        </p>
      </div>

      {/* Quick Config */}
      <div className="glass rounded-xl p-4">
        <div className="flex gap-3">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value as AIProvider)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
          >
            <option value="gemini">Gemini</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Claude</option>
            <option value="lmstudio">LM Studio</option>
          </select>
          {provider !== 'lmstudio' && (
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="API Key"
              className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
            />
          )}
        </div>
      </div>

      <VideoInput onVideoSelected={handleAnalyze} disabled={loading} />

      {loading && <Loader message="Running quick analysis..." />}

      {error && (
        <div className="rounded-lg bg-error/10 px-4 py-3 text-error">{error}</div>
      )}

      {result && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-bold text-text-primary">
              Top Clips ({result.clips.length})
            </h2>
            <span className="text-sm text-text-muted">
              {(result.processingTime / 1000).toFixed(1)}s via {result.provider}
            </span>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {result.clips.map((clip: Clip, i: number) => (
              <ClipCard key={clip.id} clip={clip} index={i} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
