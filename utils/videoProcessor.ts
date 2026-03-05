/**
 * Video Processor Utilities
 *
 * Helper functions for video file handling, validation,
 * and metadata extraction in the browser.
 */

const SUPPORTED_FORMATS = ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-matroska'];
const MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024; // 2 GB

export interface VideoMetadata {
  duration: number;
  width: number;
  height: number;
  aspectRatio: string;
  fileSize: number;
  format: string;
}

/**
 * Validate a video file before processing.
 */
export function validateVideoFile(file: File): string | null {
  if (!SUPPORTED_FORMATS.includes(file.type)) {
    return `Unsupported format: ${file.type}. Supported: MP4, WebM, MOV, MKV`;
  }
  if (file.size > MAX_FILE_SIZE) {
    return `File too large (${formatBytes(file.size)}). Maximum: 2 GB`;
  }
  if (file.size === 0) {
    return 'File is empty';
  }
  return null;
}

/**
 * Extract video metadata using an HTML5 video element.
 */
export function getVideoMetadata(file: File): Promise<VideoMetadata> {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'metadata';

    const url = URL.createObjectURL(file);
    video.src = url;

    video.onloadedmetadata = () => {
      const metadata: VideoMetadata = {
        duration: video.duration,
        width: video.videoWidth,
        height: video.videoHeight,
        aspectRatio: `${video.videoWidth}:${video.videoHeight}`,
        fileSize: file.size,
        format: file.type,
      };
      URL.revokeObjectURL(url);
      resolve(metadata);
    };

    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load video metadata'));
    };
  });
}

/**
 * Generate a thumbnail from a video file at the given timestamp.
 */
export function generateThumbnail(
  file: File,
  timestamp: number = 0,
  width: number = 320
): Promise<string> {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    video.preload = 'auto';
    video.muted = true;

    const url = URL.createObjectURL(file);
    video.src = url;

    video.onloadeddata = () => {
      video.currentTime = Math.min(timestamp, video.duration);
    };

    video.onseeked = () => {
      const canvas = document.createElement('canvas');
      const scale = width / video.videoWidth;
      canvas.width = width;
      canvas.height = video.videoHeight * scale;

      const ctx = canvas.getContext('2d');
      if (!ctx) {
        URL.revokeObjectURL(url);
        reject(new Error('Canvas context unavailable'));
        return;
      }

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
      URL.revokeObjectURL(url);
      resolve(dataUrl);
    };

    video.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to generate thumbnail'));
    };
  });
}

/**
 * Check if a YouTube URL is valid and extract the video ID.
 */
export function parseYouTubeUrl(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
    /youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  return null;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}
