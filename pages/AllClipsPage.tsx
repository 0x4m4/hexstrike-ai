import { useState, useEffect } from 'react';
import { collection, query, where, getDocs } from 'firebase/firestore';
import { db } from '@/firebase';
import { useAuth } from '@/hooks/useAuth';
import { useDebounce } from '@/hooks/useDebounce';
import { ClipCard } from '@/components/ClipCard';
import type { Clip, Platform, Project } from '@/types';
import { PLATFORM_CONFIGS } from '@/types';

export function AllClipsPage() {
  const { user } = useAuth();
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [platformFilter, setPlatformFilter] = useState<Platform | 'all'>('all');
  const [sortBy, setSortBy] = useState<'score' | 'duration' | 'recent'>('score');

  const debouncedSearch = useDebounce(search, 300);

  useEffect(() => {
    if (!user) return;

    const load = async () => {
      const q = query(collection(db, 'projects'), where('userId', '==', user.uid));
      const snapshot = await getDocs(q);
      const allClips: Clip[] = [];
      snapshot.docs.forEach((doc) => {
        const project = doc.data() as Project;
        if (project.clips) {
          allClips.push(...project.clips);
        }
      });
      setClips(allClips);
      setLoading(false);
    };

    load().catch(() => setLoading(false));
  }, [user]);

  const filteredClips = clips
    .filter((clip) => {
      if (platformFilter !== 'all' && clip.bestPlatform !== platformFilter) return false;
      if (debouncedSearch) {
        const q = debouncedSearch.toLowerCase();
        return (
          clip.title.toLowerCase().includes(q) ||
          clip.description.toLowerCase().includes(q) ||
          clip.tags.some((t) => t.toLowerCase().includes(q))
        );
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'score') return b.viralScore.overall - a.viralScore.overall;
      if (sortBy === 'duration') return b.duration - a.duration;
      return 0;
    });

  const platforms = Object.keys(PLATFORM_CONFIGS) as Platform[];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">All Clips</h1>
        <p className="text-text-secondary">
          {clips.length} clips across all projects
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search clips..."
          className="rounded-lg border border-border bg-surface px-4 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
        />

        <select
          value={platformFilter}
          onChange={(e) => setPlatformFilter(e.target.value as Platform | 'all')}
          className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
        >
          <option value="all">All Platforms</option>
          {platforms.map((p) => (
            <option key={p} value={p}>
              {PLATFORM_CONFIGS[p].label}
            </option>
          ))}
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
        >
          <option value="score">Highest Score</option>
          <option value="duration">Longest</option>
          <option value="recent">Recent</option>
        </select>
      </div>

      {/* Results */}
      {loading ? (
        <div className="py-12 text-center text-text-muted">Loading clips...</div>
      ) : filteredClips.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <div className="mb-4 text-4xl">🎬</div>
          <h3 className="mb-2 text-lg font-semibold text-text-primary">
            {clips.length === 0 ? 'No clips yet' : 'No matching clips'}
          </h3>
          <p className="text-text-secondary">
            {clips.length === 0
              ? 'Analyze a video to start generating clips'
              : 'Try adjusting your filters'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredClips.map((clip, index) => (
            <ClipCard key={clip.id} clip={clip} index={index} />
          ))}
        </div>
      )}
    </div>
  );
}
