/**
 * Multi-LLM Service - Board of Advisors
 *
 * Orchestrates analysis across multiple AI providers simultaneously,
 * then aggregates and reconciles their recommendations into a
 * consensus result with confidence scoring.
 */

import type {
  AIProviderConfig,
  AggregatedClip,
  Clip,
  MultiLLMAnalysisResult,
  ProviderAnalysis,
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

/**
 * Run analysis across all configured providers and aggregate results.
 */
export async function boardAnalysis(
  source: VideoInputSource,
  providers: AIProviderConfig[]
): Promise<MultiLLMAnalysisResult> {
  const startTime = Date.now();

  const videoData =
    source.type === 'file'
      ? await (source.value as File).arrayBuffer()
      : (source.value as string);

  // Run all providers in parallel
  const results = await Promise.allSettled(
    providers.map(async (config): Promise<ProviderAnalysis> => {
      const providerStart = Date.now();
      const analyzeFn = PROVIDER_MAP[config.provider];
      const clips = await analyzeFn(videoData, config);
      return {
        provider: config.provider,
        clips,
        confidence: clips.length > 0 ? 0.85 : 0,
        processingTime: Date.now() - providerStart,
        model: config.model,
      };
    })
  );

  const providerResults: ProviderAnalysis[] = results.map((result, i) => {
    if (result.status === 'fulfilled') return result.value;
    return {
      provider: providers[i].provider,
      clips: [],
      confidence: 0,
      processingTime: 0,
      model: providers[i].model,
      error: result.reason?.message || 'Provider failed',
    };
  });

  const aggregatedClips = buildConsensus(providerResults);

  return {
    mode: 'board',
    providers: providerResults,
    aggregatedClips,
    totalProcessingTime: Date.now() - startTime,
    timestamp: new Date(),
    videoId: `board-${Date.now()}`,
  };
}

/**
 * Build consensus clips from multiple provider results.
 * Uses time-overlap detection to match similar clips across providers.
 */
function buildConsensus(results: ProviderAnalysis[]): AggregatedClip[] {
  const successful = results.filter((r) => r.clips.length > 0);
  if (successful.length === 0) return [];

  // Collect all clips with provider attribution
  const allClips: Array<{ clip: Clip; provider: string }> = [];
  for (const result of successful) {
    for (const clip of result.clips) {
      allClips.push({ clip, provider: result.provider });
    }
  }

  // Group overlapping clips
  const groups: Array<Array<{ clip: Clip; provider: string }>> = [];
  const used = new Set<number>();

  for (let i = 0; i < allClips.length; i++) {
    if (used.has(i)) continue;

    const group = [allClips[i]];
    used.add(i);

    for (let j = i + 1; j < allClips.length; j++) {
      if (used.has(j)) continue;
      if (clipsOverlap(allClips[i].clip, allClips[j].clip)) {
        group.push(allClips[j]);
        used.add(j);
      }
    }

    groups.push(group);
  }

  // Build aggregated clips from groups
  return groups
    .map((group) => {
      const primary = group[0].clip;
      const avgScore = Math.round(
        group.reduce((sum, g) => sum + g.clip.viralScore.overall, 0) / group.length
      );

      const uniqueProviders = new Set(group.map((g) => g.provider));

      return {
        ...primary,
        viralScore: { ...primary.viralScore, overall: avgScore },
        confidenceScore: uniqueProviders.size / successful.length,
        providerAgreement: uniqueProviders.size,
        providerVariations: group.slice(1).map((g) => ({
          provider: g.provider as ProviderAnalysis['provider'],
          viralScore: g.clip.viralScore.overall,
          startTimeDiff: g.clip.startTime - primary.startTime,
          endTimeDiff: g.clip.endTime - primary.endTime,
        })),
        consensusNotes:
          uniqueProviders.size === successful.length
            ? 'All providers agree on this clip'
            : `${uniqueProviders.size}/${successful.length} providers identified this clip`,
      } satisfies AggregatedClip;
    })
    .sort((a, b) => b.viralScore.overall - a.viralScore.overall);
}

function clipsOverlap(a: Clip, b: Clip, threshold = 5): boolean {
  return Math.abs(a.startTime - b.startTime) < threshold && Math.abs(a.endTime - b.endTime) < threshold;
}
