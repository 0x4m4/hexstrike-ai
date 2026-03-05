import type { AggregatedClip } from '@/types';
import { formatTimestamp } from '@/utils/performance';
import { PLATFORM_CONFIGS } from '@/types';
import { PROVIDER_LABELS } from '@/utils/analysisConfig';

interface MultiLLMClipCardProps {
  clip: AggregatedClip;
  index: number;
  onSelect?: (clip: AggregatedClip) => void;
  selected?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
}

export function MultiLLMClipCard({ clip, index, onSelect, selected }: MultiLLMClipCardProps) {
  const platform = PLATFORM_CONFIGS[clip.bestPlatform];
  const confidencePct = Math.round(clip.confidenceScore * 100);

  return (
    <div
      className={`glass rounded-xl p-4 transition-all hover:shadow-elevated ${
        selected ? 'ring-2 ring-primary' : ''
      }`}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
            {index + 1}
          </span>
          <h3 className="font-semibold text-text-primary">{clip.title}</h3>
        </div>
        <div className={`text-lg font-bold ${getScoreColor(clip.viralScore.overall)}`}>
          {clip.viralScore.overall}
        </div>
      </div>

      <p className="mb-3 text-sm text-text-secondary line-clamp-2">{clip.description}</p>

      {/* Consensus Badge */}
      <div className="mb-3 flex items-center gap-2">
        <div
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            clip.confidenceScore >= 0.8
              ? 'bg-green-500/20 text-green-400'
              : clip.confidenceScore >= 0.5
              ? 'bg-yellow-500/20 text-yellow-400'
              : 'bg-orange-500/20 text-orange-400'
          }`}
        >
          {confidencePct}% confidence
        </div>
        <span className="text-xs text-text-muted">
          {clip.providerAgreement} provider{clip.providerAgreement !== 1 ? 's' : ''} agree
        </span>
      </div>

      {/* Metadata */}
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

      {/* Provider Variations */}
      {clip.providerVariations.length > 0 && (
        <div className="mb-3 rounded-lg bg-surface p-2">
          <div className="mb-1 text-xs font-medium text-text-muted">Provider Scores</div>
          <div className="space-y-1">
            {clip.providerVariations.map((pv) => (
              <div key={pv.provider} className="flex items-center justify-between text-xs">
                <span className="text-text-secondary">
                  {PROVIDER_LABELS[pv.provider]}
                </span>
                <span className={`font-semibold ${getScoreColor(pv.viralScore)}`}>
                  {pv.viralScore}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Consensus Notes */}
      {clip.consensusNotes && (
        <p className="mb-3 text-xs italic text-text-muted">{clip.consensusNotes}</p>
      )}

      {/* Tags */}
      {clip.tags.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1">
          {clip.tags.slice(0, 4).map((tag) => (
            <span key={tag} className="rounded-full bg-surface px-2 py-0.5 text-xs text-text-muted">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Select */}
      {onSelect && (
        <button
          onClick={() => onSelect(clip)}
          className={`w-full rounded-lg py-2 text-sm font-medium ${
            selected
              ? 'bg-primary/20 text-primary'
              : 'bg-primary text-white hover:bg-primary-hover'
          }`}
        >
          {selected ? 'Selected' : 'Select'}
        </button>
      )}
    </div>
  );
}
