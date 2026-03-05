import { useState, useRef, useCallback } from 'react';
import { ClipPreview } from '@/components/ClipPreview';
import { trimVideo, cropVideo, getAspectRatioForPlatform } from '@/services/ffmpegService';
import { formatTimestamp, formatFileSize } from '@/utils/performance';
import type { Clip, Platform, AspectRatio } from '@/types';
import { PLATFORM_CONFIGS } from '@/types';

export function TrimClipsPage() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(30);
  const [duration, setDuration] = useState(0);
  const [platform, setPlatform] = useState<Platform>('tiktok');
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState('');
  const [exportedBlob, setExportedBlob] = useState<Blob | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setVideoFile(file);
    setExportedBlob(null);

    const url = URL.createObjectURL(file);
    setVideoUrl(url);

    const video = document.createElement('video');
    video.preload = 'metadata';
    video.src = url;
    video.onloadedmetadata = () => {
      setDuration(video.duration);
      setEndTime(Math.min(30, video.duration));
    };
  }, []);

  const handleTrim = async () => {
    if (!videoFile) return;
    setProcessing(true);
    setProgress('Trimming video...');

    try {
      const trimmed = await trimVideo({
        startTime,
        endTime,
        inputFile: videoFile,
      });

      setProgress('Applying crop...');
      const aspectRatio = getAspectRatioForPlatform(platform);
      const cropDimensions = getCropForAspectRatio(aspectRatio);

      const cropped = await cropVideo({
        inputFile: trimmed,
        crop: cropDimensions,
      });

      setExportedBlob(cropped);
      setProgress('Done!');
    } catch (err) {
      setProgress(`Error: ${err instanceof Error ? err.message : 'Failed to process'}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleDownload = () => {
    if (!exportedBlob) return;
    const url = URL.createObjectURL(exportedBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `clip_${platform}_${startTime}-${endTime}.mp4`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const platformConfigs = Object.values(PLATFORM_CONFIGS);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Trim & Crop Clips</h1>
        <p className="text-text-secondary">
          Trim video segments and auto-crop for any platform
        </p>
      </div>

      {/* File Selection */}
      {!videoFile ? (
        <div
          onClick={() => fileInputRef.current?.click()}
          className="glass cursor-pointer rounded-xl border-2 border-dashed border-border p-12 text-center hover:border-primary/50"
        >
          <div className="mb-2 text-4xl">🎬</div>
          <p className="font-medium text-text-primary">Click to select a video</p>
          <p className="text-sm text-text-muted">MP4, WebM, MOV up to 2GB</p>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Preview */}
          <div className="lg:col-span-2">
            <ClipPreview
              src={videoUrl}
              startTime={startTime}
              endTime={endTime}
              onStartTimeChange={setStartTime}
              onEndTimeChange={setEndTime}
              duration={duration}
            />
          </div>

          {/* Controls */}
          <div className="space-y-4">
            {/* Time Controls */}
            <div className="glass rounded-xl p-4">
              <h3 className="mb-3 font-semibold text-text-primary">Trim Range</h3>
              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs text-text-muted">Start</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min={0}
                      max={duration}
                      step={0.1}
                      value={startTime}
                      onChange={(e) => setStartTime(Math.min(Number(e.target.value), endTime - 1))}
                      className="flex-1"
                    />
                    <span className="w-16 text-right text-sm text-text-primary">
                      {formatTimestamp(startTime)}
                    </span>
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-text-muted">End</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min={0}
                      max={duration}
                      step={0.1}
                      value={endTime}
                      onChange={(e) => setEndTime(Math.max(Number(e.target.value), startTime + 1))}
                      className="flex-1"
                    />
                    <span className="w-16 text-right text-sm text-text-primary">
                      {formatTimestamp(endTime)}
                    </span>
                  </div>
                </div>
                <div className="text-center text-sm text-text-muted">
                  Duration: {(endTime - startTime).toFixed(1)}s
                </div>
              </div>
            </div>

            {/* Platform */}
            <div className="glass rounded-xl p-4">
              <h3 className="mb-3 font-semibold text-text-primary">Target Platform</h3>
              <div className="space-y-1">
                {platformConfigs.map((config) => (
                  <button
                    key={config.platform}
                    onClick={() => setPlatform(config.platform)}
                    className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-all ${
                      platform === config.platform
                        ? 'bg-primary text-white'
                        : 'text-text-secondary hover:bg-surface-hover'
                    }`}
                  >
                    <span>{config.icon} {config.label}</span>
                    <span className="text-xs opacity-70">{config.aspectRatio}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <button
              onClick={handleTrim}
              disabled={processing}
              className="w-full rounded-xl bg-primary py-3 font-medium text-white hover:bg-primary-hover disabled:opacity-50"
            >
              {processing ? progress : 'Trim & Export'}
            </button>

            {exportedBlob && (
              <button
                onClick={handleDownload}
                className="w-full rounded-xl bg-success py-3 font-medium text-white hover:opacity-90"
              >
                Download ({formatFileSize(exportedBlob.size)})
              </button>
            )}

            <button
              onClick={() => {
                setVideoFile(null);
                setVideoUrl('');
                setExportedBlob(null);
              }}
              className="w-full rounded-lg bg-surface py-2 text-sm text-text-secondary hover:bg-surface-hover"
            >
              Choose Different Video
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function getCropForAspectRatio(ratio: AspectRatio) {
  switch (ratio) {
    case '9:16':
      return { x: 420, y: 0, width: 1080, height: 1920 };
    case '1:1':
      return { x: 420, y: 0, width: 1080, height: 1080 };
    case '16:9':
    default:
      return { x: 0, y: 0, width: 1920, height: 1080 };
  }
}
