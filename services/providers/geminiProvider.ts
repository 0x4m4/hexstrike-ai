/**
 * Gemini AI Provider
 *
 * Uses Google's GenAI SDK to analyze video content.
 * Supports both file upload and frame extraction approaches.
 */

import type { AIProviderConfig, Clip, ViralScoreBreakdown, AudioAnalysis, Platform } from '@/types';

const ANALYSIS_PROMPT = `You are a professional video content analyst. Analyze this video and identify the most engaging, viral-worthy clips.

For each clip, provide:
1. Title and description
2. Start and end timestamps (in seconds)
3. Viral score breakdown (0-100 for each): overall, engagement, shareability, retention, trendAlignment
4. Score explanation
5. Audio analysis: musicIntensity (0-1), speechCoverage (0-1), hasSpeech, hasMusic, tempo estimate
6. Key moments with timestamps, type (emotional-peak/action/transition/speech/visual-hook), and confidence
7. Best platform recommendation (tiktok/youtube-shorts/instagram-reels/youtube/twitter)
8. Relevant tags

Return valid JSON array of clips. Focus on moments that would perform well on social media.`;

interface GeminiClipResponse {
  title: string;
  description: string;
  startTime: number;
  endTime: number;
  viralScore: ViralScoreBreakdown;
  audioAnalysis: Partial<AudioAnalysis>;
  keyMoments: { timestamp: number; type: string; confidence: number; description: string }[];
  bestPlatform: string;
  tags: string[];
}

export async function analyzeWithGemini(
  videoData: string | ArrayBuffer,
  config: AIProviderConfig
): Promise<Clip[]> {
  const { GoogleGenAI } = await import('@google/genai');
  const genai = new GoogleGenAI({ apiKey: config.apiKey });

  const model = config.model || 'gemini-2.0-flash';

  const response = await genai.models.generateContent({
    model,
    contents: [
      {
        role: 'user',
        parts: [
          { text: ANALYSIS_PROMPT },
          typeof videoData === 'string'
            ? { text: `Video URL: ${videoData}` }
            : {
                inlineData: {
                  mimeType: 'video/mp4',
                  data: arrayBufferToBase64(videoData),
                },
              },
        ],
      },
    ],
    config: {
      maxOutputTokens: config.maxTokens || 4096,
      temperature: config.temperature ?? 0.3,
    },
  });

  const text = response.text ?? '';
  return parseClipsFromResponse(text);
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function parseClipsFromResponse(text: string): Clip[] {
  // Extract JSON from response (may be wrapped in markdown code blocks)
  const jsonMatch = text.match(/\[[\s\S]*\]/);
  if (!jsonMatch) return [];

  try {
    const rawClips: GeminiClipResponse[] = JSON.parse(jsonMatch[0]);
    return rawClips.map((raw, index) => ({
      id: `gemini-clip-${index}-${Date.now()}`,
      title: raw.title || `Clip ${index + 1}`,
      description: raw.description || '',
      startTime: raw.startTime || 0,
      endTime: raw.endTime || 0,
      duration: (raw.endTime || 0) - (raw.startTime || 0),
      viralScore: {
        overall: clamp(raw.viralScore?.overall ?? 50),
        engagement: clamp(raw.viralScore?.engagement ?? 50),
        shareability: clamp(raw.viralScore?.shareability ?? 50),
        retention: clamp(raw.viralScore?.retention ?? 50),
        trendAlignment: clamp(raw.viralScore?.trendAlignment ?? 50),
        explanation: raw.viralScore?.explanation || '',
      },
      audioAnalysis: {
        musicIntensity: raw.audioAnalysis?.musicIntensity ?? 0,
        speechCoverage: raw.audioAnalysis?.speechCoverage ?? 0,
        emotionalPeaks: raw.audioAnalysis?.emotionalPeaks ?? [],
        volumeDynamics: raw.audioAnalysis?.volumeDynamics ?? [],
        tempo: raw.audioAnalysis?.tempo ?? 120,
        hasSpeech: raw.audioAnalysis?.hasSpeech ?? false,
        hasMusic: raw.audioAnalysis?.hasMusic ?? false,
      },
      keyMoments: (raw.keyMoments || []).map((km) => ({
        timestamp: km.timestamp,
        type: km.type as Clip['keyMoments'][0]['type'],
        confidence: km.confidence,
        description: km.description,
      })),
      cropCoordinates: {
        '16:9': { x: 0, y: 0, width: 1920, height: 1080 },
        '9:16': { x: 420, y: 0, width: 1080, height: 1920 },
        '1:1': { x: 420, y: 0, width: 1080, height: 1080 },
      },
      bestPlatform: (raw.bestPlatform || 'tiktok') as Platform,
      tags: raw.tags || [],
    }));
  } catch {
    console.error('Failed to parse Gemini response');
    return [];
  }
}

function clamp(value: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, value));
}
