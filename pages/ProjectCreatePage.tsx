import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { collection, addDoc, serverTimestamp } from 'firebase/firestore';
import { db } from '@/firebase';
import { useAuth } from '@/hooks/useAuth';
import type { Platform, AnalysisMode, AIProvider } from '@/types';
import { getAvailablePlatforms } from '@/utils/analysisConfig';

export function ProjectCreatePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [platforms, setPlatforms] = useState<Platform[]>(['tiktok', 'youtube-shorts', 'instagram-reels']);
  const [mode, setMode] = useState<AnalysisMode>('single');
  const [saving, setSaving] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !name.trim()) return;

    setSaving(true);
    try {
      const docRef = await addDoc(collection(db, 'projects'), {
        userId: user.uid,
        name: name.trim(),
        description: description.trim(),
        status: 'draft',
        settings: {
          targetPlatforms: platforms,
          analysisMode: mode,
          providers: [] as AIProvider[],
          maxClips: 10,
          minViralScore: 30,
          language: 'en',
        },
        stats: {
          totalClips: 0,
          averageViralScore: 0,
          topPlatform: null,
          analysisCount: 0,
          lastAnalyzedAt: null,
        },
        tags: [],
        collaborators: [],
        clips: [],
        analyses: [],
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      });
      navigate(`/projects/${docRef.id}`);
    } catch (err) {
      console.error('Failed to create project:', err);
      setSaving(false);
    }
  };

  const availablePlatforms = getAvailablePlatforms();

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold text-text-primary">Create New Project</h1>

      <form onSubmit={handleCreate} className="glass rounded-xl p-6 space-y-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-text-secondary">Project Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="My Video Project"
            className="w-full rounded-lg border border-border bg-surface px-4 py-3 text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-text-secondary">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="What is this project about?"
            className="w-full rounded-lg border border-border bg-surface px-4 py-3 text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none resize-none"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-text-secondary">Target Platforms</label>
          <div className="flex flex-wrap gap-2">
            {availablePlatforms.map((p) => (
              <button
                key={p.value}
                type="button"
                onClick={() =>
                  setPlatforms((prev) =>
                    prev.includes(p.value)
                      ? prev.filter((x) => x !== p.value)
                      : [...prev, p.value]
                  )
                }
                className={`rounded-lg px-3 py-2 text-sm transition-all ${
                  platforms.includes(p.value)
                    ? 'bg-primary text-white'
                    : 'bg-surface text-text-secondary hover:bg-surface-hover'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-text-secondary">Default Analysis Mode</label>
          <div className="grid grid-cols-3 gap-2">
            {(['single', 'board', 'quick'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`rounded-lg py-2 text-sm font-medium transition-all ${
                  mode === m
                    ? 'bg-primary text-white'
                    : 'bg-surface text-text-secondary hover:bg-surface-hover'
                }`}
              >
                {m === 'single' ? 'Single AI' : m === 'board' ? 'Board' : 'Quick'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate('/projects')}
            className="flex-1 rounded-lg bg-surface py-3 font-medium text-text-secondary hover:bg-surface-hover"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving || !name.trim()}
            className="flex-1 rounded-lg bg-primary py-3 font-medium text-white hover:bg-primary-hover disabled:opacity-50"
          >
            {saving ? 'Creating...' : 'Create Project'}
          </button>
        </div>
      </form>
    </div>
  );
}
