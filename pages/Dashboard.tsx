import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useAnalyses } from '@/hooks/useAnalyses';
import { VideoInput } from '@/components/VideoInput';
import { LLMSelector } from '@/components/LLMSelector';
import { ClipCard } from '@/components/ClipCard';
import { Loader } from '@/components/Loader';
import { DEFAULT_ANALYSIS_CONFIG, createProviderConfig } from '@/utils/analysisConfig';
import type { AIProvider, AIProviderConfig, AnalysisMode, Clip, VideoInputSource, MultiLLMAnalysisResult } from '@/types';

export function Dashboard() {
  const { profile } = useAuth();
  const { progress, result, isAnalyzing, error, startAnalysis, reset } = useAnalyses();

  const [mode, setMode] = useState<AnalysisMode>('single');
  const [providers, setProviders] = useState<AIProviderConfig[]>([]);
  const [apiKeys, setApiKeys] = useState<Record<AIProvider, string>>({
    gemini: '',
    openai: '',
    anthropic: '',
    lmstudio: '',
  });
  const [selectedClips, setSelectedClips] = useState<Set<string>>(new Set());

  const handleApiKeyChange = (provider: AIProvider, key: string) => {
    setApiKeys((prev) => ({ ...prev, [provider]: key }));
    setProviders((prev) =>
      prev.map((p) => (p.provider === provider ? { ...p, apiKey: key } : p))
    );
  };

  const handleAnalyze = async (source: VideoInputSource) => {
    const activeProviders = providers
      .filter((p) => p.apiKey || p.provider === 'lmstudio')
      .map((p) => createProviderConfig(p.provider, p.apiKey, p.model));

    if (activeProviders.length === 0) {
      return;
    }

    await startAnalysis(source, {
      ...DEFAULT_ANALYSIS_CONFIG,
      mode,
      providers: activeProviders,
    });
  };

  const toggleClipSelection = (clip: Clip) => {
    setSelectedClips((prev) => {
      const next = new Set(prev);
      if (next.has(clip.id)) next.delete(clip.id);
      else next.add(clip.id);
      return next;
    });
  };

  const clips = result
    ? 'aggregatedClips' in result
      ? (result as MultiLLMAnalysisResult).aggregatedClips
      : result.clips
    : [];

  return (
    <div className="space-y-6">
      {/* Welcome */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">
          Welcome back, {profile?.displayName || 'Creator'}
        </h1>
        <p className="text-text-secondary">
          {profile?.credits.remaining ?? 0} analysis credits remaining
        </p>
      </div>

      {/* Configuration */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <VideoInput onVideoSelected={handleAnalyze} disabled={isAnalyzing} />
        </div>
        <div>
          <LLMSelector
            mode={mode}
            onModeChange={setMode}
            providers={providers}
            onProvidersChange={setProviders}
            apiKeys={apiKeys}
            onApiKeyChange={handleApiKeyChange}
          />
        </div>
      </div>

      {/* Progress */}
      {isAnalyzing && <Loader progress={progress ?? undefined} />}

      {/* Error */}
      {error && (
        <div className="glass rounded-xl border-l-4 border-error p-4">
          <p className="font-medium text-error">Analysis Failed</p>
          <p className="text-sm text-text-secondary">{error}</p>
          <button onClick={reset} className="mt-2 text-sm text-primary hover:underline">
            Try Again
          </button>
        </div>
      )}

      {/* Results */}
      {clips.length > 0 && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-bold text-text-primary">
              Detected Clips ({clips.length})
            </h2>
            {selectedClips.size > 0 && (
              <span className="text-sm text-primary">{selectedClips.size} selected</span>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {clips.map((clip, index) => (
              <ClipCard
                key={clip.id}
                clip={clip}
                index={index}
                selected={selectedClips.has(clip.id)}
                onSelect={toggleClipSelection}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
