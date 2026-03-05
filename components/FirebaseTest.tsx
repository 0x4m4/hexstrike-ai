import { useState } from 'react';
import { doc, getDoc, setDoc, deleteDoc, serverTimestamp } from 'firebase/firestore';
import { db, auth } from '@/firebase';

export function FirebaseTest() {
  const [status, setStatus] = useState<'idle' | 'testing' | 'pass' | 'fail'>('idle');
  const [message, setMessage] = useState('');

  const runTests = async () => {
    setStatus('testing');
    const results: string[] = [];

    // Test 1: Auth state
    try {
      const user = auth.currentUser;
      results.push(`Auth: ${user ? `Signed in as ${user.email}` : 'Not signed in'}`);
    } catch (err) {
      results.push(`Auth: FAIL - ${err instanceof Error ? err.message : 'Unknown'}`);
    }

    // Test 2: Firestore read
    try {
      const testRef = doc(db, '_test', 'connection');
      await getDoc(testRef);
      results.push('Firestore Read: OK');
    } catch (err) {
      results.push(`Firestore Read: FAIL - ${err instanceof Error ? err.message : 'Unknown'}`);
    }

    // Test 3: Firestore write (if authenticated)
    if (auth.currentUser) {
      try {
        const testRef = doc(db, '_test', `test-${Date.now()}`);
        await setDoc(testRef, { test: true, timestamp: serverTimestamp() });
        await deleteDoc(testRef);
        results.push('Firestore Write: OK');
      } catch (err) {
        results.push(`Firestore Write: FAIL - ${err instanceof Error ? err.message : 'Unknown'}`);
      }
    }

    const allPassed = results.every((r) => !r.includes('FAIL'));
    setStatus(allPassed ? 'pass' : 'fail');
    setMessage(results.join('\n'));
  };

  if (import.meta.env.PROD) return null;

  return (
    <div className="glass rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">Firebase Connection Test</h3>
        <span
          className={`h-2 w-2 rounded-full ${
            status === 'pass' ? 'bg-green-400' : status === 'fail' ? 'bg-red-400' : 'bg-gray-400'
          }`}
        />
      </div>
      <button
        onClick={runTests}
        disabled={status === 'testing'}
        className="mb-2 rounded-lg bg-surface px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-hover disabled:opacity-50"
      >
        {status === 'testing' ? 'Testing...' : 'Run Tests'}
      </button>
      {message && (
        <pre className="rounded bg-surface p-2 text-xs text-text-muted whitespace-pre-wrap">
          {message}
        </pre>
      )}
    </div>
  );
}
