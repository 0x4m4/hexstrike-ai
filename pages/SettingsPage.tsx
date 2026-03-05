import { useState } from 'react';
import { doc, updateDoc } from 'firebase/firestore';
import { db } from '@/firebase';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/components/ThemeProvider';
import type { AIProvider, AnalysisMode, Platform } from '@/types';
import { PROVIDER_LABELS, getAvailablePlatforms } from '@/utils/analysisConfig';

export function SettingsPage() {
  const { user, profile } = useAuth();
  const { theme, setTheme } = useTheme();
  const [saving, setSaving] = useState(false);
  const [defaultProvider, setDefaultProvider] = useState<AIProvider>(profile?.preferences.defaultProvider || 'gemini');
  const [defaultMode, setDefaultMode] = useState<AnalysisMode>(profile?.preferences.defaultMode || 'single');
  const [defaultPlatforms, setDefaultPlatforms] = useState<Platform[]>(
    profile?.preferences.defaultPlatforms || ['tiktok', 'youtube-shorts', 'instagram-reels']
  );

  const handleSave = async () => {
    if (!user) return;
    setSaving(true);
    try {
      await updateDoc(doc(db, 'users', user.uid), {
        'preferences.defaultProvider': defaultProvider,
        'preferences.defaultMode': defaultMode,
        'preferences.defaultPlatforms': defaultPlatforms,
        'preferences.theme': theme,
      });
    } catch (err) {
      console.error('Failed to save settings:', err);
    }
    setSaving(false);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold text-text-primary">Settings</h1>

      {/* Account */}
      <section className="glass rounded-xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Account</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-text-muted">Email</span>
            <span className="text-text-primary">{profile?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Plan</span>
            <span className="capitalize text-primary">{profile?.subscription}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-muted">Credits</span>
            <span className="text-text-primary">
              {profile?.credits.remaining} / {profile?.credits.total}
            </span>
          </div>
        </div>
      </section>

      {/* Theme */}
      <section className="glass rounded-xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Appearance</h2>
        <div className="grid grid-cols-3 gap-2">
          {(['light', 'dark', 'system'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`rounded-lg py-2 text-sm font-medium capitalize transition-all ${
                theme === t ? 'bg-primary text-white' : 'bg-surface text-text-secondary hover:bg-surface-hover'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </section>

      {/* Defaults */}
      <section className="glass rounded-xl p-6 space-y-4">
        <h2 className="text-lg font-semibold text-text-primary">Analysis Defaults</h2>

        <div>
          <label className="mb-1 block text-sm text-text-muted">Default Provider</label>
          <select
            value={defaultProvider}
            onChange={(e) => setDefaultProvider(e.target.value as AIProvider)}
            className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-text-primary focus:border-primary focus:outline-none"
          >
            {Object.entries(PROVIDER_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm text-text-muted">Default Mode</label>
          <div className="grid grid-cols-3 gap-2">
            {(['single', 'board', 'quick'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setDefaultMode(m)}
                className={`rounded-lg py-2 text-sm font-medium capitalize ${
                  defaultMode === m ? 'bg-primary text-white' : 'bg-surface text-text-secondary hover:bg-surface-hover'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm text-text-muted">Default Platforms</label>
          <div className="flex flex-wrap gap-2">
            {getAvailablePlatforms().map((p) => (
              <button
                key={p.value}
                onClick={() =>
                  setDefaultPlatforms((prev) =>
                    prev.includes(p.value) ? prev.filter((x) => x !== p.value) : [...prev, p.value]
                  )
                }
                className={`rounded-lg px-3 py-1.5 text-sm ${
                  defaultPlatforms.includes(p.value) ? 'bg-primary text-white' : 'bg-surface text-text-secondary'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full rounded-lg bg-primary py-3 font-medium text-white hover:bg-primary-hover disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </section>
    </div>
  );
}
