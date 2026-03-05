/**
 * Gemini Service - Direct Gemini Integration
 *
 * Wraps the Gemini provider with file upload support and
 * higher-level utilities for direct Gemini-specific workflows.
 */

import { analyzeWithGemini } from './providers/geminiProvider';
import type { AIProviderConfig, Clip, VideoInputSource } from '@/types';

const DEFAULT_CONFIG: AIProviderConfig = {
  provider: 'gemini',
  apiKey: '',
  model: 'gemini-2.0-flash',
  maxTokens: 4096,
  temperature: 0.3,
};

/**
 * Analyze a video using Gemini with file upload support.
 */
export async function analyzeWithGeminiDirect(
  source: VideoInputSource,
  apiKey: string,
  model?: string
): Promise<Clip[]> {
  const config: AIProviderConfig = {
    ...DEFAULT_CONFIG,
    apiKey,
    model: model || DEFAULT_CONFIG.model,
  };

  const videoData =
    source.type === 'file'
      ? await (source.value as File).arrayBuffer()
      : (source.value as string);

  return analyzeWithGemini(videoData, config);
}

/**
 * Upload a file to Gemini's File API for larger video support.
 */
export async function uploadToGeminiFileAPI(
  file: File,
  apiKey: string
): Promise<{ uri: string; mimeType: string }> {
  const { GoogleGenAI } = await import('@google/genai');
  const genai = new GoogleGenAI({ apiKey });

  const result = await genai.files.upload({
    file,
    config: { mimeType: file.type },
  });

  return {
    uri: result.uri ?? '',
    mimeType: file.type,
  };
}

/**
 * List available Gemini models.
 */
export function getGeminiModels(): string[] {
  return ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'];
}
