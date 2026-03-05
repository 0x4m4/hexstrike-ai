/**
 * OpenAI Provider
 *
 * Analyzes video content using OpenAI's GPT-4 Vision API.
 * Sends video frames as images for analysis.
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

export async function analyzeWithOpenAI(
  videoData: string | ArrayBuffer,
  config: AIProviderConfig
): Promise<Clip[]> {
  const model = config.model || 'gpt-4o';
  const messages: Array<{ role: string; content: unknown }> = [
    {
      role: 'user',
      content: typeof videoData === 'string'
        ? [
            { type: 'text', text: `${ANALYSIS_PROMPT}\n\nVideo URL: ${videoData}` },
          ]
        : [
            { type: 'text', text: ANALYSIS_PROMPT },
            {
              type: 'image_url',
              image_url: {
                url: `data:image/jpeg;base64,${arrayBufferToBase64(videoData)}`,
              },
            },
          ],
    },
  ];

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model,
      messages,
      max_tokens: config.maxTokens || 4096,
      temperature: config.temperature ?? 0.3,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(`OpenAI API error: ${response.status} - ${(error as { error?: { message?: string } }).error?.message || 'Unknown error'}`);
  }

  const data = await response.json();
  const text = data.choices?.[0]?.message?.content || '';
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
      id: `openai-clip-${index}-${Date.now()}`,
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
        musicIntensity: (raw.audioAnalysis as Record<string, number>)?.musicIntensity ?? 0,
        speechCoverage: (raw.audioAnalysis as Record<string, number>)?.speechCoverage ?? 0,
        emotionalPeaks: [],
        volumeDynamics: [],
        tempo: (raw.audioAnalysis as Record<string, number>)?.tempo ?? 120,
        hasSpeech: (raw.audioAnalysis as Record<string, boolean>)?.hasSpeech ?? false,
        hasMusic: (raw.audioAnalysis as Record<string, boolean>)?.hasMusic ?? false,
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
    console.error('Failed to parse OpenAI response');
    return [];
  }
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}
