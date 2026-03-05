import type { Clip } from '@/types';
import { formatTimestamp } from '@/utils/performance';
import { PLATFORM_CONFIGS } from '@/types';

interface ClipCardProps {
  clip: Clip;
  index: number;
  onSelect?: (clip: Clip) => void;
  onPreview?: (clip: Clip) => void;
  selected?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
}

function getScoreBg(score: number): string {
  if (score >= 80) return 'bg-green-500/20 border-green-500/30';
  if (score >= 60) return 'bg-yellow-500/20 border-yellow-500/30';
  if (score >= 40) return 'bg-orange-500/20 border-orange-500/30';
  return 'bg-red-500/20 border-red-500/30';
}

export function ClipCard({ clip, index, onSelect, onPreview, selected }: ClipCardProps) {
  const platform = PLATFORM_CONFIGS[clip.bestPlatform];

  return (
    <div
      className={`glass rounded-xl p-4 transition-all hover:shadow-elevated ${
        selected ? 'ring-2 ring-primary' : ''
      }`}
    >
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
            {index + 1}
          </span>
          <h3 className="font-semibold text-text-primary">{clip.title}</h3>
        </div>
        <div
          className={`rounded-lg border px-2 py-1 text-lg font-bold ${getScoreBg(
            clip.viralScore.overall
          )} ${getScoreColor(clip.viralScore.overall)}`}
        >
          {clip.viralScore.overall}
        </div>
      </div>

      <p className="mb-3 text-sm text-text-secondary line-clamp-2">{clip.description}</p>

      <div className="mb-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded-md bg-surface px-2 py-1 text-text-muted">
          {formatTimestamp(clip.startTime)} - {formatTimestamp(clip.endTime)}
        </span>
        <span className="rounded-md bg-surface px-2 py-1 text-text-muted">
          {clip.duration.toFixed(1)}s
        </span>
        <span className="rounded-md bg-primary/20 px-2 py-1 text-primary">
          {platform?.icon} {platform?.label}
        </span>
      </div>

      {/* Score Breakdown */}
      <div className="mb-3 grid grid-cols-4 gap-1">
        {(
          [
            ['Engage', clip.viralScore.engagement],
            ['Share', clip.viralScore.shareability],
            ['Retain', clip.viralScore.retention],
            ['Trend', clip.viralScore.trendAlignment],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="text-center">
            <div className="text-xs text-text-muted">{label}</div>
            <div className={`text-sm font-semibold ${getScoreColor(value)}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Tags */}
      {clip.tags.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {clip.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-surface px-2 py-0.5 text-xs text-text-muted"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {onPreview && (
          <button
            onClick={() => onPreview(clip)}
            className="flex-1 rounded-lg bg-surface py-2 text-sm font-medium text-text-secondary hover:bg-surface-hover"
          >
            Preview
          </button>
        )}
        {onSelect && (
          <button
            onClick={() => onSelect(clip)}
            className="flex-1 rounded-lg bg-primary py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            {selected ? 'Selected' : 'Select'}
          </button>
        )}
      </div>
    </div>
  );
}
