/**
 * LLM Service - Central AI Orchestration
 *
 * Routes analysis requests to the appropriate provider(s),
 * handles multi-LLM "Board of Advisors" mode, and aggregates results.
 */

import type {
  AIProvider,
  AIProviderConfig,
  AnalysisConfig,
  AnalysisProgress,
  Clip,
  MultiLLMAnalysisResult,
  ProviderAnalysis,
  AggregatedClip,
  QuickAnalysisResult,
  VideoInputSource,
} from '@/types';
import { analyzeWithGemini } from './providers/geminiProvider';
import { analyzeWithOpenAI } from './providers/openaiProvider';
import { analyzeWithAnthropic } from './providers/anthropicProvider';
import { analyzeWithLMStudio } from './providers/lmstudioProvider';

type ProgressCallback = (progress: AnalysisProgress) => void;

const PROVIDER_FUNCTIONS: Record<
  AIProvider,
  (data: string | ArrayBuffer, config: AIProviderConfig) => Promise<Clip[]>
> = {
  gemini: analyzeWithGemini,
  openai: analyzeWithOpenAI,
  anthropic: analyzeWithAnthropic,
  lmstudio: analyzeWithLMStudio,
};

/**
 * Main entry point for video analysis.
 * Dispatches to single, board, or quick mode.
 */
export async function analyzeVideo(
  source: VideoInputSource,
  config: AnalysisConfig,
  onProgress: ProgressCallback
): Promise<MultiLLMAnalysisResult | QuickAnalysisResult> {
  const videoData = await resolveVideoSource(source, onProgress);

  if (config.mode === 'quick') {
    return performQuickAnalysis(videoData, config, onProgress);
  }

  if (config.mode === 'board') {
    return performBoardAnalysis(videoData, config, onProgress);
  }

  return performSingleAnalysis(videoData, config, onProgress);
}

async function resolveVideoSource(
  source: VideoInputSource,
  onProgress: ProgressCallback
): Promise<string | ArrayBuffer> {
  onProgress({ stage: 'uploading', progress: 10, message: 'Processing video input...' });

  if (source.type === 'url' || source.type === 'youtube') {
    return source.value as string;
  }

  // File upload - read as ArrayBuffer
  const file = source.value as File;
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      onProgress({ stage: 'extracting', progress: 30, message: 'Video loaded' });
      resolve(reader.result as ArrayBuffer);
    };
    reader.onerror = () => reject(new Error('Failed to read video file'));
    reader.readAsArrayBuffer(file);
  });
}

async function performSingleAnalysis(
  videoData: string | ArrayBuffer,
  config: AnalysisConfig,
  onProgress: ProgressCallback
): Promise<MultiLLMAnalysisResult> {
  const provider = config.providers[0];
  onProgress({
    stage: 'analyzing',
    progress: 40,
    message: `Analyzing with ${provider.provider}...`,
    provider: provider.provider,
  });

  const startTime = Date.now();
  const analyzeFn = PROVIDER_FUNCTIONS[provider.provider];
  const clips = await analyzeFn(videoData, provider);
  const processingTime = Date.now() - startTime;

  const filteredClips = filterClips(clips, config);

  onProgress({ stage: 'scoring', progress: 80, message: 'Finalizing scores...' });

  const providerResult: ProviderAnalysis = {
    provider: provider.provider,
    clips: filteredClips,
    confidence: 0.85,
    processingTime,
    model: provider.model,
  };

  return {
    mode: 'single',
    providers: [providerResult],
    aggregatedClips: filteredClips.map((clip) => ({
      ...clip,
      confidenceScore: 0.85,
      providerAgreement: 1,
      providerVariations: [],
      consensusNotes: `Single provider analysis by ${provider.provider}`,
    })),
    totalProcessingTime: processingTime,
    timestamp: new Date(),
    videoId: `video-${Date.now()}`,
  };
}

async function performBoardAnalysis(
  videoData: string | ArrayBuffer,
  config: AnalysisConfig,
  onProgress: ProgressCallback
): Promise<MultiLLMAnalysisResult> {
  const startTime = Date.now();
  const results: ProviderAnalysis[] = [];

  // Run all providers concurrently
  const promises = config.providers.map(async (providerConfig, index) => {
    onProgress({
      stage: 'analyzing',
      progress: 40 + index * 10,
      message: `Analyzing with ${providerConfig.provider}...`,
      provider: providerConfig.provider,
    });

    const providerStart = Date.now();
    try {
      const analyzeFn = PROVIDER_FUNCTIONS[providerConfig.provider];
      const clips = await analyzeFn(videoData, providerConfig);
      return {
        provider: providerConfig.provider,
        clips: filterClips(clips, config),
        confidence: 0.85,
        processingTime: Date.now() - providerStart,
        model: providerConfig.model,
      } satisfies ProviderAnalysis;
    } catch (err) {
      return {
        provider: providerConfig.provider,
        clips: [],
        confidence: 0,
        processingTime: Date.now() - providerStart,
        model: providerConfig.model,
        error: err instanceof Error ? err.message : 'Unknown error',
      } satisfies ProviderAnalysis;
    }
  });

  const providerResults = await Promise.all(promises);
  results.push(...providerResults);

  onProgress({ stage: 'scoring', progress: 85, message: 'Aggregating results across providers...' });

  const aggregatedClips = aggregateClips(results);
  const totalProcessingTime = Date.now() - startTime;

  return {
    mode: 'board',
    providers: results,
    aggregatedClips,
    totalProcessingTime,
    timestamp: new Date(),
    videoId: `video-${Date.now()}`,
  };
}

async function performQuickAnalysis(
  videoData: string | ArrayBuffer,
  config: AnalysisConfig,
  onProgress: ProgressCallback
): Promise<QuickAnalysisResult> {
  const provider = config.providers[0];
  onProgress({
    stage: 'analyzing',
    progress: 50,
    message: `Quick analysis with ${provider.provider}...`,
    provider: provider.provider,
  });

  const startTime = Date.now();
  const analyzeFn = PROVIDER_FUNCTIONS[provider.provider];
  const clips = await analyzeFn(videoData, provider);

  // Quick mode: return top 3-5 clips sorted by viral score
  const topClips = filterClips(clips, config)
    .sort((a, b) => b.viralScore.overall - a.viralScore.overall)
    .slice(0, 5);

  return {
    clips: topClips,
    confidence: 0.8,
    processingTime: Date.now() - startTime,
    provider: provider.provider,
    model: provider.model,
  };
}

function filterClips(clips: Clip[], config: AnalysisConfig): Clip[] {
  return clips.filter((clip) => {
    if (clip.duration < config.minDuration) return false;
    if (clip.duration > config.maxDuration) return false;
    if (clip.viralScore.overall < config.minViralScore) return false;
    return true;
  }).slice(0, config.maxClips);
}

/**
 * Aggregate clips from multiple providers using time-overlap matching.
 * Clips from different providers that overlap significantly are merged.
 */
function aggregateClips(results: ProviderAnalysis[]): AggregatedClip[] {
  const successfulResults = results.filter((r) => r.clips.length > 0);
  if (successfulResults.length === 0) return [];

  // Use the first provider's clips as anchors
  const anchor = successfulResults[0];
  const aggregated: AggregatedClip[] = [];

  for (const clip of anchor.clips) {
    const variations: AggregatedClip['providerVariations'] = [];
    let totalScore = clip.viralScore.overall;
    let matchCount = 1;

    for (let i = 1; i < successfulResults.length; i++) {
      const otherClips = successfulResults[i].clips;
      const match = otherClips.find(
        (other) =>
          Math.abs(other.startTime - clip.startTime) < 5 &&
          Math.abs(other.endTime - clip.endTime) < 5
      );

      if (match) {
        matchCount++;
        totalScore += match.viralScore.overall;
        variations.push({
          provider: successfulResults[i].provider,
          viralScore: match.viralScore.overall,
          startTimeDiff: match.startTime - clip.startTime,
          endTimeDiff: match.endTime - clip.endTime,
        });
      }
    }

    aggregated.push({
      ...clip,
      viralScore: {
        ...clip.viralScore,
        overall: Math.round(totalScore / matchCount),
      },
      confidenceScore: matchCount / successfulResults.length,
      providerAgreement: matchCount,
      providerVariations: variations,
      consensusNotes:
        matchCount === successfulResults.length
          ? 'All providers agree on this clip'
          : `${matchCount}/${successfulResults.length} providers identified this clip`,
    });
  }

  return aggregated.sort((a, b) => b.viralScore.overall - a.viralScore.overall);
}
