import { useState, useEffect } from 'react';
import { collection, query, where, orderBy, getDocs } from 'firebase/firestore';
import { db } from '@/firebase';
import { useAuth } from '@/hooks/useAuth';
import { formatDuration } from '@/utils/performance';

interface AnalysisHistoryItem {
  id: string;
  videoId: string;
  mode: string;
  providers: string[];
  clipCount: number;
  avgScore: number;
  processingTime: number;
  timestamp: Date;
}

export function HistoryPage() {
  const { user } = useAuth();
  const [history, setHistory] = useState<AnalysisHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;

    const load = async () => {
      const q = query(
        collection(db, 'analyses'),
        where('userId', '==', user.uid),
        orderBy('timestamp', 'desc')
      );
      const snapshot = await getDocs(q);
      const items = snapshot.docs.map((doc) => ({
        id: doc.id,
        ...doc.data(),
      })) as AnalysisHistoryItem[];
      setHistory(items);
      setLoading(false);
    };

    load().catch(() => setLoading(false));
  }, [user]);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-text-primary">Analysis History</h1>

      {loading ? (
        <div className="py-12 text-center text-text-muted">Loading history...</div>
      ) : history.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center">
          <div className="mb-4 text-4xl">📋</div>
          <h3 className="mb-2 text-lg font-semibold text-text-primary">No analyses yet</h3>
          <p className="text-text-secondary">Your analysis history will appear here</p>
        </div>
      ) : (
        <div className="space-y-3">
          {history.map((item) => (
            <div key={item.id} className="glass flex items-center justify-between rounded-xl p-4">
              <div>
                <div className="font-medium text-text-primary">
                  {item.mode === 'board' ? 'Board of Advisors' : item.mode === 'quick' ? 'Quick Scan' : 'Single AI'} Analysis
                </div>
                <div className="text-sm text-text-muted">
                  {item.providers.join(', ')} &middot; {item.clipCount} clips found
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium text-primary">
                  Avg Score: {item.avgScore}
                </div>
                <div className="text-xs text-text-muted">
                  {formatDuration(item.processingTime)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
