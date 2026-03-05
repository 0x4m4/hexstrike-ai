/**
 * Analysis Configuration Defaults
 *
 * Provides sensible defaults for analysis configuration
 * and validation utilities.
 */

import type { AnalysisConfig, AIProvider, AIProviderConfig, Platform } from '@/types';

export const DEFAULT_ANALYSIS_CONFIG: AnalysisConfig = {
  mode: 'single',
  providers: [],
  targetPlatforms: ['tiktok', 'youtube-shorts', 'instagram-reels'],
  maxClips: 10,
  minDuration: 5,
  maxDuration: 180,
  minViralScore: 30,
  language: 'en',
  includeTranscript: true,
  includeAudioAnalysis: true,
};

export const PROVIDER_MODELS: Record<AIProvider, string[]> = {
  gemini: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  anthropic: ['claude-sonnet-4-20250514', 'claude-haiku-4-5-20251001'],
  lmstudio: ['local-model'],
};

export const PROVIDER_LABELS: Record<AIProvider, string> = {
  gemini: 'Google Gemini',
  openai: 'OpenAI',
  anthropic: 'Anthropic Claude',
  lmstudio: 'LM Studio (Local)',
};

export function createProviderConfig(
  provider: AIProvider,
  apiKey: string,
  model?: string
): AIProviderConfig {
  return {
    provider,
    apiKey,
    model: model || PROVIDER_MODELS[provider][0],
    maxTokens: 4096,
    temperature: 0.3,
  };
}

export function getAvailablePlatforms(): Array<{ value: Platform; label: string }> {
  return [
    { value: 'tiktok', label: 'TikTok' },
    { value: 'youtube-shorts', label: 'YouTube Shorts' },
    { value: 'instagram-reels', label: 'Instagram Reels' },
    { value: 'youtube', label: 'YouTube' },
    { value: 'twitter', label: 'Twitter/X' },
  ];
}

export function validateConfig(config: Partial<AnalysisConfig>): string[] {
  const errors: string[] = [];
  if (!config.providers || config.providers.length === 0) {
    errors.push('At least one AI provider must be configured');
  }
  if (config.providers) {
    for (const p of config.providers) {
      if (!p.apiKey && p.provider !== 'lmstudio') {
        errors.push(`API key required for ${PROVIDER_LABELS[p.provider]}`);
      }
    }
  }
  if (config.maxClips !== undefined && (config.maxClips < 1 || config.maxClips > 50)) {
    errors.push('Max clips must be between 1 and 50');
  }
  return errors;
}
