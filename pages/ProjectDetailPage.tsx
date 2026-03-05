import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { doc, getDoc } from 'firebase/firestore';
import { db } from '@/firebase';
import { ClipCard } from '@/components/ClipCard';
import { Loader } from '@/components/Loader';
import type { Project } from '@/types';

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    const load = async () => {
      const snap = await getDoc(doc(db, 'projects', id));
      if (snap.exists()) {
        setProject({ id: snap.id, ...snap.data() } as Project);
      }
      setLoading(false);
    };
    load().catch(() => setLoading(false));
  }, [id]);

  if (loading) return <Loader message="Loading project..." />;

  if (!project) {
    return (
      <div className="py-12 text-center">
        <h2 className="text-xl font-bold text-text-primary">Project not found</h2>
        <Link to="/projects" className="mt-4 inline-block text-primary hover:underline">
          Back to Projects
        </Link>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link to="/projects" className="mb-2 inline-block text-sm text-text-muted hover:text-primary">
          &larr; Back to Projects
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{project.name}</h1>
            <p className="text-text-secondary">{project.description}</p>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-sm ${
              project.status === 'completed'
                ? 'bg-green-500/20 text-green-400'
                : 'bg-blue-500/20 text-blue-400'
            }`}
          >
            {project.status}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-6 grid grid-cols-4 gap-4">
        {[
          { label: 'Total Clips', value: project.stats.totalClips },
          { label: 'Avg Score', value: project.stats.averageViralScore || '-' },
          { label: 'Analyses', value: project.stats.analysisCount },
          { label: 'Platforms', value: project.settings.targetPlatforms.length },
        ].map((stat) => (
          <div key={stat.label} className="glass rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-text-primary">{stat.value}</div>
            <div className="text-xs text-text-muted">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Clips */}
      {project.clips.length > 0 ? (
        <div>
          <h2 className="mb-4 text-lg font-semibold text-text-primary">Clips</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {project.clips.map((clip, i) => (
              <ClipCard key={clip.id} clip={clip} index={i} />
            ))}
          </div>
        </div>
      ) : (
        <div className="glass rounded-xl p-8 text-center">
          <p className="text-text-secondary">No clips yet. Run an analysis to detect viral moments.</p>
        </div>
      )}
    </div>
  );
}
