/**
 * Quick Analysis Service
 *
 * Provides a streamlined analysis mode that returns
 * top clips with confidence scores and best-platform
 * recommendations. Faster than full board analysis.
 */

import type {
  AIProviderConfig,
  Clip,
  Platform,
  QuickAnalysisResult,
  VideoInputSource,
} from '@/types';
import { analyzeWithGemini } from './providers/geminiProvider';
import { analyzeWithOpenAI } from './providers/openaiProvider';
import { analyzeWithAnthropic } from './providers/anthropicProvider';
import { analyzeWithLMStudio } from './providers/lmstudioProvider';

const PROVIDER_MAP = {
  gemini: analyzeWithGemini,
  openai: analyzeWithOpenAI,
  anthropic: analyzeWithAnthropic,
  lmstudio: analyzeWithLMStudio,
} as const;

export async function quickAnalyze(
  source: VideoInputSource,
  providerConfig: AIProviderConfig,
  targetPlatforms: Platform[] = ['tiktok', 'youtube-shorts', 'instagram-reels']
): Promise<QuickAnalysisResult> {
  const startTime = Date.now();

  const videoData =
    source.type === 'file'
      ? await (source.value as File).arrayBuffer()
      : (source.value as string);

  const analyzeFn = PROVIDER_MAP[providerConfig.provider];
  const clips = await analyzeFn(videoData, providerConfig);

  // Score and rank clips, filtering for target platforms
  const rankedClips = clips
    .filter((clip) => targetPlatforms.includes(clip.bestPlatform))
    .sort((a, b) => b.viralScore.overall - a.viralScore.overall)
    .slice(0, 5);

  return {
    clips: rankedClips,
    confidence: rankedClips.length > 0 ? 0.8 : 0,
    processingTime: Date.now() - startTime,
    provider: providerConfig.provider,
    model: providerConfig.model,
  };
}

/**
 * Get a quick score estimate for a single clip without full analysis.
 */
export function estimateViralScore(clip: Clip): number {
  const weights = {
    duration: clip.duration >= 15 && clip.duration <= 60 ? 10 : 0,
    hasHook: clip.keyMoments.some((m) => m.type === 'visual-hook') ? 15 : 0,
    hasEmotion: clip.keyMoments.some((m) => m.type === 'emotional-peak') ? 15 : 0,
    hasSpeech: clip.audioAnalysis.hasSpeech ? 10 : 0,
    hasMusic: clip.audioAnalysis.hasMusic ? 10 : 0,
    baseScore: clip.viralScore.overall * 0.4,
  };

  return Math.min(100, Object.values(weights).reduce((a, b) => a + b, 0));
}
