import { useState } from 'react';
import { trimVideo, cropVideo, getAspectRatioForPlatform } from '@/services/ffmpegService';
import { formatFileSize } from '@/utils/performance';
import type { Clip, Platform, AspectRatio } from '@/types';
import { PLATFORM_CONFIGS } from '@/types';

interface ExportJob {
  clip: Clip;
  platform: Platform;
  status: 'pending' | 'processing' | 'done' | 'error';
  blob?: Blob;
  error?: string;
}

export function ExportPage() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>(['tiktok', 'youtube-shorts', 'instagram-reels']);
  const [jobs, setJobs] = useState<ExportJob[]>([]);
  const [exporting, setExporting] = useState(false);

  // Load clips from sessionStorage (set by Dashboard/AllClips)
  useState(() => {
    try {
      const stored = sessionStorage.getItem('exportClips');
      if (stored) {
        setClips(JSON.parse(stored));
        sessionStorage.removeItem('exportClips');
      }
    } catch { /* ignore */ }
  });

  const togglePlatform = (platform: Platform) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    );
  };

  const handleExport = async () => {
    if (!videoFile || clips.length === 0 || selectedPlatforms.length === 0) return;

    const exportJobs: ExportJob[] = [];
    for (const clip of clips) {
      for (const platform of selectedPlatforms) {
        exportJobs.push({ clip, platform, status: 'pending' });
      }
    }
    setJobs(exportJobs);
    setExporting(true);

    for (let i = 0; i < exportJobs.length; i++) {
      const job = exportJobs[i];
      setJobs((prev) =>
        prev.map((j, idx) => (idx === i ? { ...j, status: 'processing' } : j))
      );

      try {
        const trimmed = await trimVideo({
          startTime: job.clip.startTime,
          endTime: job.clip.endTime,
          inputFile: videoFile,
        });

        const aspectRatio = getAspectRatioForPlatform(job.platform);
        const crop = getCropForRatio(aspectRatio);
        const blob = await cropVideo({ inputFile: trimmed, crop });

        setJobs((prev) =>
          prev.map((j, idx) => (idx === i ? { ...j, status: 'done', blob } : j))
        );
      } catch (err) {
        setJobs((prev) =>
          prev.map((j, idx) =>
            idx === i
              ? { ...j, status: 'error', error: err instanceof Error ? err.message : 'Failed' }
              : j
          )
        );
      }
    }

    setExporting(false);
  };

  const downloadJob = (job: ExportJob) => {
    if (!job.blob) return;
    const url = URL.createObjectURL(job.blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${job.clip.title.replace(/\s+/g, '_')}_${job.platform}.mp4`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadAll = () => {
    jobs.filter((j) => j.status === 'done' && j.blob).forEach(downloadJob);
  };

  const platforms = Object.values(PLATFORM_CONFIGS);
  const completedCount = jobs.filter((j) => j.status === 'done').length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Export Clips</h1>
        <p className="text-text-secondary">
          Export clips optimized for each platform
        </p>
      </div>

      {/* Video Source */}
      <div className="glass rounded-xl p-4">
        <h3 className="mb-3 font-semibold text-text-primary">Source Video</h3>
        {videoFile ? (
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-primary">{videoFile.name}</p>
              <p className="text-sm text-text-muted">{formatFileSize(videoFile.size)}</p>
            </div>
            <button
              onClick={() => setVideoFile(null)}
              className="text-sm text-text-muted hover:text-text-primary"
            >
              Change
            </button>
          </div>
        ) : (
          <label className="block cursor-pointer rounded-lg border border-dashed border-border p-6 text-center hover:border-primary/50">
            <p className="text-text-secondary">Select the source video file</p>
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && setVideoFile(e.target.files[0])}
            />
          </label>
        )}
      </div>

      {/* Clips to Export */}
      <div className="glass rounded-xl p-4">
        <h3 className="mb-3 font-semibold text-text-primary">
          Clips ({clips.length})
        </h3>
        {clips.length === 0 ? (
          <p className="text-sm text-text-muted">
            No clips selected. Select clips from the Dashboard or All Clips page first.
          </p>
        ) : (
          <div className="space-y-2">
            {clips.map((clip) => (
              <div
                key={clip.id}
                className="flex items-center justify-between rounded-lg bg-surface px-3 py-2"
              >
                <div>
                  <span className="text-sm font-medium text-text-primary">{clip.title}</span>
                  <span className="ml-2 text-xs text-text-muted">{clip.duration.toFixed(1)}s</span>
                </div>
                <span className="text-sm font-semibold text-primary">
                  {clip.viralScore.overall}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Platform Selection */}
      <div className="glass rounded-xl p-4">
        <h3 className="mb-3 font-semibold text-text-primary">Target Platforms</h3>
        <div className="flex flex-wrap gap-2">
          {platforms.map((config) => (
            <button
              key={config.platform}
              onClick={() => togglePlatform(config.platform)}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                selectedPlatforms.includes(config.platform)
                  ? 'bg-primary text-white'
                  : 'bg-surface text-text-secondary hover:bg-surface-hover'
              }`}
            >
              {config.icon} {config.label} ({config.aspectRatio})
            </button>
          ))}
        </div>
      </div>

      {/* Export Button */}
      <button
        onClick={handleExport}
        disabled={exporting || !videoFile || clips.length === 0 || selectedPlatforms.length === 0}
        className="w-full rounded-xl bg-primary py-3 font-medium text-white hover:bg-primary-hover disabled:opacity-50"
      >
        {exporting
          ? `Exporting... (${completedCount}/${jobs.length})`
          : `Export ${clips.length} clips for ${selectedPlatforms.length} platforms`}
      </button>

      {/* Export Progress */}
      {jobs.length > 0 && (
        <div className="glass rounded-xl p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-text-primary">Export Progress</h3>
            {completedCount > 0 && (
              <button onClick={downloadAll} className="text-sm text-primary hover:underline">
                Download All ({completedCount})
              </button>
            )}
          </div>
          <div className="space-y-2">
            {jobs.map((job, i) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg bg-surface px-3 py-2"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`h-2 w-2 rounded-full ${
                      job.status === 'done'
                        ? 'bg-green-400'
                        : job.status === 'processing'
                        ? 'animate-pulse bg-blue-400'
                        : job.status === 'error'
                        ? 'bg-red-400'
                        : 'bg-gray-400'
                    }`}
                  />
                  <span className="text-sm text-text-primary">
                    {job.clip.title} &rarr; {PLATFORM_CONFIGS[job.platform].label}
                  </span>
                </div>
                {job.status === 'done' && job.blob && (
                  <button
                    onClick={() => downloadJob(job)}
                    className="text-xs text-primary hover:underline"
                  >
                    {formatFileSize(job.blob.size)}
                  </button>
                )}
                {job.status === 'error' && (
                  <span className="text-xs text-error">{job.error}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function getCropForRatio(ratio: AspectRatio) {
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
