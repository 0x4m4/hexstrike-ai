/**
 * Instant Video Service
 *
 * Creates instant preview URLs and metadata from video files
 * without full FFmpeg processing. Uses native HTML5 video APIs
 * for fast, lightweight operations.
 */

import { getVideoMetadata, generateThumbnail, parseYouTubeUrl } from '@/utils/videoProcessor';
import type { VideoInputSource } from '@/types';

export interface InstantPreview {
  url: string;
  thumbnailUrl: string;
  duration: number;
  width: number;
  height: number;
  aspectRatio: string;
  fileSize: number;
  fileName: string;
}

/**
 * Create an instant preview from a video file.
 * Uses object URLs for zero-copy preview.
 */
export async function createInstantPreview(file: File): Promise<InstantPreview> {
  const url = URL.createObjectURL(file);
  const metadata = await getVideoMetadata(file);
  const thumbnailUrl = await generateThumbnail(file, metadata.duration * 0.1);

  return {
    url,
    thumbnailUrl,
    duration: metadata.duration,
    width: metadata.width,
    height: metadata.height,
    aspectRatio: metadata.aspectRatio,
    fileSize: file.size,
    fileName: file.name,
  };
}

/**
 * Create a preview from any video input source.
 */
export async function createPreviewFromSource(
  source: VideoInputSource
): Promise<InstantPreview | null> {
  if (source.type === 'file') {
    return createInstantPreview(source.value as File);
  }

  if (source.type === 'youtube') {
    const videoId = parseYouTubeUrl(source.value as string);
    if (!videoId) return null;

    return {
      url: source.value as string,
      thumbnailUrl: `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`,
      duration: source.duration || 0,
      width: 1920,
      height: 1080,
      aspectRatio: '16:9',
      fileSize: 0,
      fileName: `YouTube: ${videoId}`,
    };
  }

  if (source.type === 'url') {
    return {
      url: source.value as string,
      thumbnailUrl: '',
      duration: source.duration || 0,
      width: 0,
      height: 0,
      aspectRatio: 'unknown',
      fileSize: 0,
      fileName: new URL(source.value as string).pathname.split('/').pop() || 'video',
    };
  }

  return null;
}

/**
 * Revoke a previously created preview to free memory.
 */
export function revokePreview(preview: InstantPreview): void {
  if (preview.url.startsWith('blob:')) {
    URL.revokeObjectURL(preview.url);
  }
  if (preview.thumbnailUrl.startsWith('data:')) {
    // Data URLs don't need revoking
  } else if (preview.thumbnailUrl.startsWith('blob:')) {
    URL.revokeObjectURL(preview.thumbnailUrl);
  }
}

/**
 * Get video duration from a file without full metadata extraction.
 */
export function getQuickDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';
    const url = URL.createObjectURL(file);
    video.src = url;
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(video.duration);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to get video duration'));
    };
  });
}
