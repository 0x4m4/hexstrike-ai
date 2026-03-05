/**
 * Fast Video Service
 *
 * Extracts key frames from video rapidly for faster AI analysis.
 * Instead of sending full video data, sends representative frames.
 */

import { getFFmpeg } from './ffmpegService';
import { fetchFile } from '@ffmpeg/util';

export interface ExtractedFrame {
  timestamp: number;
  dataUrl: string;
  blob: Blob;
}

/**
 * Extract key frames from a video at regular intervals.
 * Returns JPEG frames suitable for sending to vision APIs.
 */
export async function extractKeyFrames(
  file: File,
  options: {
    interval?: number; // seconds between frames (default: 5)
    maxFrames?: number; // max number of frames (default: 20)
    quality?: number;   // JPEG quality 1-31, lower = better (default: 5)
  } = {}
): Promise<ExtractedFrame[]> {
  const { interval = 5, maxFrames = 20, quality = 5 } = options;

  const ffmpeg = await getFFmpeg();
  await ffmpeg.writeFile('input.mp4', await fetchFile(file));

  // Get duration
  const video = document.createElement('video');
  video.preload = 'metadata';
  const duration = await new Promise<number>((resolve) => {
    video.src = URL.createObjectURL(file);
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(video.src);
      resolve(video.duration);
    };
  });

  const frameCount = Math.min(maxFrames, Math.ceil(duration / interval));
  const frames: ExtractedFrame[] = [];

  for (let i = 0; i < frameCount; i++) {
    const timestamp = i * interval;
    const outputName = `frame_${i}.jpg`;

    await ffmpeg.exec([
      '-i', 'input.mp4',
      '-ss', timestamp.toString(),
      '-frames:v', '1',
      '-q:v', quality.toString(),
      '-vf', 'scale=640:-1',
      outputName,
    ]);

    try {
      const data = await ffmpeg.readFile(outputName);
      const blob = new Blob([data], { type: 'image/jpeg' });
      const dataUrl = await blobToDataUrl(blob);

      frames.push({ timestamp, dataUrl, blob });
      await ffmpeg.deleteFile(outputName);
    } catch {
      // Frame extraction might fail for timestamps beyond video duration
    }
  }

  await ffmpeg.deleteFile('input.mp4');
  return frames;
}

/**
 * Extract a single frame at a specific timestamp.
 */
export async function extractSingleFrame(
  file: File,
  timestamp: number
): Promise<ExtractedFrame> {
  const ffmpeg = await getFFmpeg();
  await ffmpeg.writeFile('input.mp4', await fetchFile(file));

  await ffmpeg.exec([
    '-i', 'input.mp4',
    '-ss', timestamp.toString(),
    '-frames:v', '1',
    '-q:v', '3',
    'frame.jpg',
  ]);

  const data = await ffmpeg.readFile('frame.jpg');
  const blob = new Blob([data], { type: 'image/jpeg' });
  const dataUrl = await blobToDataUrl(blob);

  await ffmpeg.deleteFile('input.mp4');
  await ffmpeg.deleteFile('frame.jpg');

  return { timestamp, dataUrl, blob };
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}
