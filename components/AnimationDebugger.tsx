import { useState } from 'react';

const ANIMATIONS = [
  { name: 'fade-in', class: 'animate-fade-in' },
  { name: 'slide-up', class: 'animate-slide-up' },
  { name: 'slide-down', class: 'animate-slide-down' },
  { name: 'scale-in', class: 'animate-scale-in' },
  { name: 'pulse-glow', class: 'animate-pulse-glow' },
  { name: 'shimmer', class: 'animate-shimmer' },
];

export function AnimationDebugger() {
  const [key, setKey] = useState(0);

  if (import.meta.env.PROD) return null;

  return (
    <div className="glass rounded-xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-text-primary">Animation Debugger</h3>
        <button
          onClick={() => setKey((k) => k + 1)}
          className="rounded-lg bg-primary px-3 py-1.5 text-sm text-white hover:bg-primary-hover"
        >
          Replay All
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3" key={key}>
        {ANIMATIONS.map((anim) => (
          <div
            key={anim.name}
            className={`rounded-lg bg-surface p-4 text-center ${anim.class}`}
          >
            <div className="mb-2 text-2xl">✨</div>
            <div className="text-sm font-medium text-text-primary">{anim.name}</div>
            <div className="text-xs text-text-muted">{anim.class}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-2">
        <h4 className="text-sm font-medium text-text-secondary">Glass Variants</h4>
        <div className="grid grid-cols-2 gap-3">
          <div className="glass rounded-lg p-3 text-center text-sm text-text-primary">
            .glass (default)
          </div>
          <div className="glass rounded-lg p-3 text-center text-sm text-text-primary shadow-elevated">
            .shadow-elevated
          </div>
        </div>
      </div>
    </div>
  );
}
