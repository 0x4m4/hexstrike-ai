/**
 * LM Studio Provider
 *
 * Connects to a local LM Studio instance for offline analysis.
 * Uses the OpenAI-compatible API format that LM Studio exposes.
 */

import type { AIProviderConfig, Clip, Platform } from '@/types';

const ANALYSIS_PROMPT = `Analyze this video content and identify the most engaging, viral-worthy clips for social media.

For each clip return a JSON object with:
- title, description
- startTime, endTime (seconds)
- viralScore: { overall, engagement, shareability, retention, trendAlignment } (0-100 each)
- viralScore.explanation (text)
- bestPlatform: tiktok|youtube-shorts|instagram-reels|youtube|twitter
- tags: string[]

Return ONLY a valid JSON array of clips.`;

export async function analyzeWithLMStudio(
  videoData: string | ArrayBuffer,
  config: AIProviderConfig
): Promise<Clip[]> {
  const endpoint = config.endpoint || 'http://localhost:1234/v1';
  const model = config.model || 'local-model';

  const prompt =
    typeof videoData === 'string'
      ? `${ANALYSIS_PROMPT}\n\nVideo URL: ${videoData}`
      : `${ANALYSIS_PROMPT}\n\n[Video data provided - analyze based on available context]`;

  const response = await fetch(`${endpoint}/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model,
      messages: [{ role: 'user', content: prompt }],
      max_tokens: config.maxTokens || 4096,
      temperature: config.temperature ?? 0.3,
    }),
  });

  if (!response.ok) {
    throw new Error(`LM Studio error: ${response.status} - ${response.statusText}`);
  }

  const data = await response.json();
  const text = data.choices?.[0]?.message?.content || '';
  return parseClips(text);
}

function parseClips(text: string): Clip[] {
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) return [];

  try {
    const rawClips = JSON.parse(jsonMatch[0]);
    return rawClips.map((raw: Record<string, unknown>, index: number) => ({
      id: `lmstudio-clip-${index}-${Date.now()}`,
      title: (raw.title as string) || `Clip ${index + 1}`,
      description: (raw.description as string) || '',
      startTime: (raw.startTime as number) || 0,
      endTime: (raw.endTime as number) || 0,
      duration: ((raw.endTime as number) || 0) - ((raw.startTime as number) || 0),
      viralScore: {
        overall: clamp((raw.viralScore as Record<string, number>)?.overall ?? 50),
        engagement: clamp((raw.viralScore as Record<string, number>)?.engagement ?? 50),
        shareability: clamp((raw.viralScore as Record<string, number>)?.shareability ?? 50),
        retention: clamp((raw.viralScore as Record<string, number>)?.retention ?? 50),
        trendAlignment: clamp((raw.viralScore as Record<string, number>)?.trendAlignment ?? 50),
        explanation: (raw.viralScore as Record<string, string>)?.explanation || '',
      },
      audioAnalysis: {
        musicIntensity: 0,
        speechCoverage: 0,
        emotionalPeaks: [],
        volumeDynamics: [],
        tempo: 120,
        hasSpeech: false,
        hasMusic: false,
      },
      keyMoments: [],
      cropCoordinates: {
        '16:9': { x: 0, y: 0, width: 1920, height: 1080 },
        '9:16': { x: 420, y: 0, width: 1080, height: 1920 },
        '1:1': { x: 420, y: 0, width: 1080, height: 1080 },
      },
      bestPlatform: ((raw.bestPlatform as string) || 'tiktok') as Platform,
      tags: Array.isArray(raw.tags) ? raw.tags : [],
    }));
  } catch {
    console.error('Failed to parse LM Studio response');
    return [];
  }
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}
