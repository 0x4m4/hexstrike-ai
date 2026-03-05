import type { AnalysisConfig, Platform } from '@/types';
import { getAvailablePlatforms } from '@/utils/analysisConfig';

interface AnalysisSettingsProps {
  config: AnalysisConfig;
  onChange: (config: AnalysisConfig) => void;
}

export function AnalysisSettings({ config, onChange }: AnalysisSettingsProps) {
  const platforms = getAvailablePlatforms();

  const update = <K extends keyof AnalysisConfig>(key: K, value: AnalysisConfig[K]) => {
    onChange({ ...config, [key]: value });
  };

  const togglePlatform = (platform: Platform) => {
    const current = config.targetPlatforms;
    update(
      'targetPlatforms',
      current.includes(platform)
        ? current.filter((p) => p !== platform)
        : [...current, platform]
    );
  };

  return (
    <div className="glass rounded-xl p-6 space-y-5">
      <h3 className="text-lg font-semibold text-text-primary">Analysis Settings</h3>

      {/* Max Clips */}
      <div>
        <label className="mb-1 flex items-center justify-between text-sm">
          <span className="text-text-secondary">Max Clips</span>
          <span className="font-medium text-text-primary">{config.maxClips}</span>
        </label>
        <input
          type="range"
          min={1}
          max={50}
          value={config.maxClips}
          onChange={(e) => update('maxClips', Number(e.target.value))}
          className="w-full"
        />
      </div>

      {/* Min Viral Score */}
      <div>
        <label className="mb-1 flex items-center justify-between text-sm">
          <span className="text-text-secondary">Min Viral Score</span>
          <span className="font-medium text-text-primary">{config.minViralScore}</span>
        </label>
        <input
          type="range"
          min={0}
          max={90}
          step={5}
          value={config.minViralScore}
          onChange={(e) => update('minViralScore', Number(e.target.value))}
          className="w-full"
        />
      </div>

      {/* Duration Range */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-sm text-text-secondary">Min Duration (s)</label>
          <input
            type="number"
            min={1}
            max={config.maxDuration - 1}
            value={config.minDuration}
            onChange={(e) => update('minDuration', Number(e.target.value))}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-text-secondary">Max Duration (s)</label>
          <input
            type="number"
            min={config.minDuration + 1}
            max={600}
            value={config.maxDuration}
            onChange={(e) => update('maxDuration', Number(e.target.value))}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      {/* Target Platforms */}
      <div>
        <label className="mb-2 block text-sm text-text-secondary">Target Platforms</label>
        <div className="flex flex-wrap gap-2">
          {platforms.map((p) => (
            <button
              key={p.value}
              onClick={() => togglePlatform(p.value)}
              className={`rounded-lg px-3 py-1.5 text-sm transition-all ${
                config.targetPlatforms.includes(p.value)
                  ? 'bg-primary text-white'
                  : 'bg-surface text-text-secondary hover:bg-surface-hover'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Toggles */}
      <div className="space-y-2">
        <label className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Include Transcript</span>
          <button
            onClick={() => update('includeTranscript', !config.includeTranscript)}
            className={`relative h-6 w-11 rounded-full transition-colors ${
              config.includeTranscript ? 'bg-primary' : 'bg-surface'
            }`}
          >
            <div
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                config.includeTranscript ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </label>
        <label className="flex items-center justify-between">
          <span className="text-sm text-text-secondary">Audio Analysis</span>
          <button
            onClick={() => update('includeAudioAnalysis', !config.includeAudioAnalysis)}
            className={`relative h-6 w-11 rounded-full transition-colors ${
              config.includeAudioAnalysis ? 'bg-primary' : 'bg-surface'
            }`}
          >
            <div
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${
                config.includeAudioAnalysis ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </label>
      </div>

      {/* Language */}
      <div>
        <label className="mb-1 block text-sm text-text-secondary">Language</label>
        <select
          value={config.language}
          onChange={(e) => update('language', e.target.value)}
          className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
        >
          <option value="en">English</option>
          <option value="es">Spanish</option>
          <option value="fr">French</option>
          <option value="de">German</option>
          <option value="ja">Japanese</option>
          <option value="ko">Korean</option>
          <option value="zh">Chinese</option>
          <option value="ar">Arabic</option>
        </select>
      </div>
    </div>
  );
}
