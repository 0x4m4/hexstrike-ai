import { useState, useEffect, useMemo } from 'react';
import { collection, query, where, getDocs } from 'firebase/firestore';
import { db } from '@/firebase';
import { useAuth } from '@/hooks/useAuth';
import type { Clip, Platform, Project } from '@/types';
import { PLATFORM_CONFIGS } from '@/types';

export function AnalyticsPage() {
  const { user } = useAuth();
  const [clips, setClips] = useState<Clip[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;

    const load = async () => {
      const q = query(collection(db, 'projects'), where('userId', '==', user.uid));
      const snapshot = await getDocs(q);
      const allClips: Clip[] = [];
      snapshot.docs.forEach((doc) => {
        const project = doc.data() as Project;
        if (project.clips) allClips.push(...project.clips);
      });
      setClips(allClips);
      setLoading(false);
    };

    load().catch(() => setLoading(false));
  }, [user]);

  const stats = useMemo(() => {
    if (clips.length === 0) return null;

    const avgScore = Math.round(
      clips.reduce((sum, c) => sum + c.viralScore.overall, 0) / clips.length
    );

    const platformCounts: Record<string, number> = {};
    clips.forEach((c) => {
      platformCounts[c.bestPlatform] = (platformCounts[c.bestPlatform] || 0) + 1;
    });

    const topPlatform = Object.entries(platformCounts).sort((a, b) => b[1] - a[1])[0];

    const scoreBuckets = { '90-100': 0, '70-89': 0, '50-69': 0, '30-49': 0, '0-29': 0 };
    clips.forEach((c) => {
      const s = c.viralScore.overall;
      if (s >= 90) scoreBuckets['90-100']++;
      else if (s >= 70) scoreBuckets['70-89']++;
      else if (s >= 50) scoreBuckets['50-69']++;
      else if (s >= 30) scoreBuckets['30-49']++;
      else scoreBuckets['0-29']++;
    });

    const avgDuration = Math.round(clips.reduce((sum, c) => sum + c.duration, 0) / clips.length);

    const topClips = [...clips].sort((a, b) => b.viralScore.overall - a.viralScore.overall).slice(0, 5);

    const avgBreakdown = {
      engagement: Math.round(clips.reduce((s, c) => s + c.viralScore.engagement, 0) / clips.length),
      shareability: Math.round(clips.reduce((s, c) => s + c.viralScore.shareability, 0) / clips.length),
      retention: Math.round(clips.reduce((s, c) => s + c.viralScore.retention, 0) / clips.length),
      trendAlignment: Math.round(clips.reduce((s, c) => s + c.viralScore.trendAlignment, 0) / clips.length),
    };

    return { avgScore, platformCounts, topPlatform, scoreBuckets, avgDuration, topClips, avgBreakdown };
  }, [clips]);

  if (loading) {
    return <div className="py-12 text-center text-text-muted">Loading analytics...</div>;
  }

  if (!stats) {
    return (
      <div>
        <h1 className="mb-6 text-2xl font-bold text-text-primary">Analytics</h1>
        <div className="glass rounded-xl p-12 text-center">
          <div className="mb-4 text-4xl">📊</div>
          <h3 className="mb-2 text-lg font-semibold text-text-primary">No data yet</h3>
          <p className="text-text-secondary">Analyze some videos to see analytics</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary">Analytics</h1>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          { label: 'Total Clips', value: clips.length, color: 'text-primary' },
          { label: 'Avg Viral Score', value: stats.avgScore, color: getScoreColor(stats.avgScore) },
          { label: 'Avg Duration', value: `${stats.avgDuration}s`, color: 'text-text-primary' },
          {
            label: 'Top Platform',
            value: stats.topPlatform ? PLATFORM_CONFIGS[stats.topPlatform[0] as Platform]?.label || stats.topPlatform[0] : '-',
            color: 'text-primary',
          },
        ].map((card) => (
          <div key={card.label} className="glass rounded-xl p-4 text-center">
            <div className={`text-3xl font-bold ${card.color}`}>{card.value}</div>
            <div className="text-xs text-text-muted">{card.label}</div>
          </div>
        ))}
      </div>

      {/* Score Breakdown */}
      <div className="glass rounded-xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Average Score Breakdown</h2>
        <div className="space-y-3">
          {(
            [
              ['Engagement', stats.avgBreakdown.engagement],
              ['Shareability', stats.avgBreakdown.shareability],
              ['Retention', stats.avgBreakdown.retention],
              ['Trend Alignment', stats.avgBreakdown.trendAlignment],
            ] as const
          ).map(([label, value]) => (
            <div key={label}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-text-secondary">{label}</span>
                <span className={`font-semibold ${getScoreColor(value)}`}>{value}</span>
              </div>
              <div className="h-2 rounded-full bg-surface">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Score Distribution */}
      <div className="glass rounded-xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Score Distribution</h2>
        <div className="space-y-2">
          {Object.entries(stats.scoreBuckets).map(([range, count]) => (
            <div key={range} className="flex items-center gap-3">
              <span className="w-16 text-sm text-text-muted">{range}</span>
              <div className="flex-1">
                <div className="h-6 rounded bg-surface">
                  <div
                    className="flex h-full items-center rounded bg-primary/30 px-2 text-xs font-medium text-primary"
                    style={{ width: `${Math.max(5, (count / clips.length) * 100)}%` }}
                  >
                    {count}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Platform Breakdown */}
      <div className="glass rounded-xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Platform Distribution</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {Object.entries(stats.platformCounts).map(([platform, count]) => {
            const config = PLATFORM_CONFIGS[platform as Platform];
            return (
              <div key={platform} className="rounded-lg bg-surface p-3 text-center">
                <div className="text-xl">{config?.icon}</div>
                <div className="text-lg font-bold text-text-primary">{count}</div>
                <div className="text-xs text-text-muted">{config?.label || platform}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Clips */}
      <div className="glass rounded-xl p-6">
        <h2 className="mb-4 text-lg font-semibold text-text-primary">Top 5 Clips</h2>
        <div className="space-y-2">
          {stats.topClips.map((clip, i) => (
            <div
              key={clip.id}
              className="flex items-center justify-between rounded-lg bg-surface px-4 py-3"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-bold text-white">
                  {i + 1}
                </span>
                <div>
                  <div className="text-sm font-medium text-text-primary">{clip.title}</div>
                  <div className="text-xs text-text-muted">
                    {clip.duration.toFixed(1)}s &middot; {PLATFORM_CONFIGS[clip.bestPlatform]?.label}
                  </div>
                </div>
              </div>
              <span className={`text-lg font-bold ${getScoreColor(clip.viralScore.overall)}`}>
                {clip.viralScore.overall}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
}
