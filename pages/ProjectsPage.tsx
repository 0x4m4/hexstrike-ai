import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { collection, query, where, orderBy, getDocs } from 'firebase/firestore';
import { db } from '@/firebase';
import { useAuth } from '@/hooks/useAuth';
import type { Project } from '@/types';

export function ProjectsPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;

    const loadProjects = async () => {
      const q = query(
        collection(db, 'projects'),
        where('userId', '==', user.uid),
        orderBy('updatedAt', 'desc')
      );
      const snapshot = await getDocs(q);
      const data = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }) as Project);
      setProjects(data);
      setLoading(false);
    };

    loadProjects().catch(() => setLoading(false));
  }, [user]);

  const statusColors: Record<string, string> = {
    draft: 'bg-gray-500/20 text-gray-400',
    analyzing: 'bg-blue-500/20 text-blue-400',
    completed: 'bg-green-500/20 text-green-400',
    archived: 'bg-yellow-500/20 text-yellow-400',
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Projects</h1>
          <p className="text-text-secondary">Manage your video analysis projects</p>
        </div>
        <Link
          to="/projects/new"
          className="rounded-lg bg-primary px-4 py-2 font-medium text-white hover:bg-primary-hover"
        >
          New Project
        </Link>
      </div>

      {loading ? (
        <div className="py-12 text-center text-text-muted">Loading projects...</div>
      ) : projects.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <div className="mb-4 text-4xl">📁</div>
          <h3 className="mb-2 text-lg font-semibold text-text-primary">No projects yet</h3>
          <p className="mb-4 text-text-secondary">Create your first project to start analyzing videos</p>
          <Link
            to="/projects/new"
            className="inline-block rounded-lg bg-primary px-6 py-2 text-white hover:bg-primary-hover"
          >
            Create Project
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/projects/${project.id}`}
              className="glass rounded-xl p-5 transition-all hover:shadow-elevated"
            >
              <div className="mb-3 flex items-start justify-between">
                <h3 className="font-semibold text-text-primary">{project.name}</h3>
                <span className={`rounded-full px-2 py-0.5 text-xs ${statusColors[project.status]}`}>
                  {project.status}
                </span>
              </div>
              <p className="mb-3 text-sm text-text-secondary line-clamp-2">{project.description}</p>
              <div className="flex gap-3 text-xs text-text-muted">
                <span>{project.stats.totalClips} clips</span>
                {project.stats.averageViralScore > 0 && (
                  <span>Avg score: {project.stats.averageViralScore}</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
