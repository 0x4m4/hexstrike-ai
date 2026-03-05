/**
 * Anthropic Provider
 *
 * Analyzes video content using Anthropic's Claude API.
 * Uses vision capabilities for frame-based analysis.
 */

import type { AIProviderConfig, Clip, Platform } from '@/types';

const ANALYSIS_PROMPT = `Analyze this video content and identify the most engaging, viral-worthy clips for social media.

For each clip return a JSON object with:
- title, description
- startTime, endTime (seconds)
- viralScore: { overall, engagement, shareability, retention, trendAlignment } (0-100 each)
- viralScore.explanation (text)
- audioAnalysis: { musicIntensity, speechCoverage (0-1), hasSpeech, hasMusic, tempo }
- keyMoments: [{ timestamp, type, confidence, description }]
- bestPlatform: tiktok|youtube-shorts|instagram-reels|youtube|twitter
- tags: string[]

Return ONLY a valid JSON array of clips.`;

export async function analyzeWithAnthropic(
  videoData: string | ArrayBuffer,
  config: AIProviderConfig
): Promise<Clip[]> {
  const model = config.model || 'claude-sonnet-4-20250514';

  const content =
    typeof videoData === 'string'
      ? [{ type: 'text', text: `${ANALYSIS_PROMPT}\n\nVideo URL: ${videoData}` }]
      : [
          { type: 'text', text: ANALYSIS_PROMPT },
          {
            type: 'image',
            source: {
              type: 'base64',
              media_type: 'image/jpeg',
              data: arrayBufferToBase64(videoData),
            },
          },
        ];

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': config.apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model,
      max_tokens: config.maxTokens || 4096,
      temperature: config.temperature ?? 0.3,
      messages: [{ role: 'user', content }],
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      `Anthropic API error: ${response.status} - ${(error as { error?: { message?: string } }).error?.message || 'Unknown error'}`
    );
  }

  const data = await response.json();
  const text = data.content?.[0]?.text || '';
  return parseClips(text);
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function parseClips(text: string): Clip[] {
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) return [];

  try {
    const rawClips = JSON.parse(jsonMatch[0]);
    return rawClips.map((raw: Record<string, unknown>, index: number) => ({
      id: `anthropic-clip-${index}-${Date.now()}`,
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
      keyMoments: Array.isArray(raw.keyMoments) ? raw.keyMoments : [],
      cropCoordinates: {
        '16:9': { x: 0, y: 0, width: 1920, height: 1080 },
        '9:16': { x: 420, y: 0, width: 1080, height: 1920 },
        '1:1': { x: 420, y: 0, width: 1080, height: 1080 },
      },
      bestPlatform: ((raw.bestPlatform as string) || 'tiktok') as Platform,
      tags: Array.isArray(raw.tags) ? raw.tags : [],
    }));
  } catch {
    console.error('Failed to parse Anthropic response');
    return [];
  }
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}
