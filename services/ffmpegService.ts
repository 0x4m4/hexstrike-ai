/**
 * FFmpeg Service - Client-Side Video Processing
 *
 * Uses FFmpeg compiled to WebAssembly for browser-based
 * video trimming, format conversion, and aspect ratio cropping.
 * No server-side processing required.
 */

import { FFmpeg } from '@ffmpeg/ffmpeg';
import { fetchFile, toBlobURL } from '@ffmpeg/util';
import type { AspectRatio, CropCoordinates, Platform } from '@/types';

let ffmpegInstance: FFmpeg | null = null;
let loadingPromise: Promise<FFmpeg> | null = null;

/**
 * Load and initialize the FFmpeg WASM instance (singleton).
 * Uses CDN-hosted core files for cross-origin isolation.
 */
export async function getFFmpeg(): Promise<FFmpeg> {
  if (ffmpegInstance?.loaded) return ffmpegInstance;
  if (loadingPromise) return loadingPromise;

  loadingPromise = (async () => {
    const ffmpeg = new FFmpeg();

    ffmpeg.on('log', ({ message }) => {
      console.debug('[FFmpeg]', message);
    });

    const baseURL = '/ffmpeg';

    await ffmpeg.load({
      coreURL: await toBlobURL(`${baseURL}/ffmpeg-core.js`, 'text/javascript'),
      wasmURL: await toBlobURL(`${baseURL}/ffmpeg-core.wasm`, 'application/wasm'),
      workerURL: await toBlobURL(`${baseURL}/ffmpeg-core.worker.js`, 'text/javascript'),
    });

    ffmpegInstance = ffmpeg;
    return ffmpeg;
  })();

  return loadingPromise;
}

export interface TrimOptions {
  startTime: number;
  endTime: number;
  inputFile: File | Blob;
  outputFormat?: string;
}

/**
 * Trim a video segment from the source file.
 */
export async function trimVideo(options: TrimOptions): Promise<Blob> {
  const { startTime, endTime, inputFile, outputFormat = 'mp4' } = options;
  const ffmpeg = await getFFmpeg();

  const inputName = 'input.mp4';
  const outputName = `output.${outputFormat}`;

  await ffmpeg.writeFile(inputName, await fetchFile(inputFile));

  await ffmpeg.exec([
    '-i', inputName,
    '-ss', startTime.toString(),
    '-to', endTime.toString(),
    '-c', 'copy',
    '-avoid_negative_ts', 'make_zero',
    outputName,
  ]);

  const data = await ffmpeg.readFile(outputName);
  const blob = new Blob([data], { type: `video/${outputFormat}` });

  // Cleanup
  await ffmpeg.deleteFile(inputName);
  await ffmpeg.deleteFile(outputName);

  return blob;
}

export interface CropOptions {
  inputFile: File | Blob;
  crop: CropCoordinates;
  startTime?: number;
  endTime?: number;
  outputFormat?: string;
}

/**
 * Crop and optionally trim a video to specific dimensions.
 */
export async function cropVideo(options: CropOptions): Promise<Blob> {
  const { inputFile, crop, startTime, endTime, outputFormat = 'mp4' } = options;
  const ffmpeg = await getFFmpeg();

  const inputName = 'input.mp4';
  const outputName = `cropped.${outputFormat}`;

  await ffmpeg.writeFile(inputName, await fetchFile(inputFile));

  const args = ['-i', inputName];

  if (startTime !== undefined) args.push('-ss', startTime.toString());
  if (endTime !== undefined) args.push('-to', endTime.toString());

  args.push(
    '-vf', `crop=${crop.width}:${crop.height}:${crop.x}:${crop.y}`,
    '-c:a', 'copy',
    outputName
  );

  await ffmpeg.exec(args);

  const data = await ffmpeg.readFile(outputName);
  const blob = new Blob([data], { type: `video/${outputFormat}` });

  await ffmpeg.deleteFile(inputName);
  await ffmpeg.deleteFile(outputName);

  return blob;
}

/**
 * Get the recommended aspect ratio for a platform.
 */
export function getAspectRatioForPlatform(platform: Platform): AspectRatio {
  switch (platform) {
    case 'tiktok':
    case 'youtube-shorts':
    case 'instagram-reels':
      return '9:16';
    case 'youtube':
    case 'twitter':
      return '16:9';
    default:
      return '16:9';
  }
}

/**
 * Extract a thumbnail frame from a video at the specified timestamp.
 */
export async function extractThumbnail(
  inputFile: File | Blob,
  timestamp: number
): Promise<Blob> {
  const ffmpeg = await getFFmpeg();

  await ffmpeg.writeFile('input.mp4', await fetchFile(inputFile));

  await ffmpeg.exec([
    '-i', 'input.mp4',
    '-ss', timestamp.toString(),
    '-frames:v', '1',
    '-q:v', '2',
    'thumbnail.jpg',
  ]);

  const data = await ffmpeg.readFile('thumbnail.jpg');
  const blob = new Blob([data], { type: 'image/jpeg' });

  await ffmpeg.deleteFile('input.mp4');
  await ffmpeg.deleteFile('thumbnail.jpg');

  return blob;
}
