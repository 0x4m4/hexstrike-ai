import { Link } from 'react-router-dom';
import { LogoIcon } from '@/components/icons/LogoIcon';

const FEATURES = [
  {
    title: 'Multi-AI Analysis',
    description: 'Board of Advisors mode runs Gemini, GPT-4, Claude, and local models simultaneously for consensus-driven clip detection.',
    icon: '🤖',
  },
  {
    title: 'Viral Score Engine',
    description: 'Every clip gets rated on engagement, shareability, retention, and trend alignment with detailed AI explanations.',
    icon: '📊',
  },
  {
    title: 'Smart Auto-Crop',
    description: 'Automatically generates crop coordinates for TikTok (9:16), YouTube (16:9), Instagram, and more.',
    icon: '✂️',
  },
  {
    title: 'Browser-Based Processing',
    description: 'FFmpeg WebAssembly powers client-side video trimming and export. No uploads to external servers.',
    icon: '⚡',
  },
  {
    title: 'Platform Optimization',
    description: 'AI recommends the best platform for each clip based on content type, duration, and trending patterns.',
    icon: '🎯',
  },
  {
    title: 'Project Management',
    description: 'Organize videos into projects with tags, notes, brand guidelines, and full analysis history.',
    icon: '📁',
  },
];

const PLATFORMS = [
  { name: 'TikTok', icon: '🎵' },
  { name: 'YouTube Shorts', icon: '📱' },
  { name: 'Instagram Reels', icon: '📸' },
  { name: 'YouTube', icon: '▶️' },
  { name: 'Twitter/X', icon: '🐦' },
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Hero */}
      <section className="relative overflow-hidden px-4 pb-20 pt-32">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent" />
        <div className="relative mx-auto max-w-4xl text-center">
          <div className="mb-6 flex justify-center">
            <LogoIcon className="h-16 w-16" />
          </div>
          <h1 className="mb-4 text-5xl font-bold tracking-tight text-text-primary sm:text-6xl">
            AI-Powered Video
            <span className="block text-primary">Clip Detection</span>
          </h1>
          <p className="mx-auto mb-8 max-w-2xl text-lg text-text-secondary">
            OpenClipPro uses multiple AI models to find the most viral-worthy moments in your videos.
            Auto-crop for any platform. Export in seconds. All in your browser.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              to="/dashboard"
              className="rounded-xl bg-primary px-8 py-4 text-lg font-semibold text-white shadow-lg hover:bg-primary-hover hover:shadow-xl transition-all"
            >
              Get Started Free
            </Link>
            <Link
              to="/about"
              className="rounded-xl border border-border bg-surface px-8 py-4 text-lg font-semibold text-text-primary hover:bg-surface-hover transition-all"
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Platforms */}
      <section className="border-y border-border bg-surface/50 py-8">
        <div className="mx-auto max-w-4xl">
          <p className="mb-4 text-center text-sm text-text-muted">Optimized for</p>
          <div className="flex items-center justify-center gap-8">
            {PLATFORMS.map((p) => (
              <div key={p.name} className="flex items-center gap-2 text-text-secondary">
                <span className="text-xl">{p.icon}</span>
                <span className="text-sm font-medium">{p.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="mb-12 text-center text-3xl font-bold text-text-primary">
            Everything You Need
          </h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="glass rounded-xl p-6 transition-all hover:shadow-elevated"
              >
                <div className="mb-3 text-3xl">{feature.icon}</div>
                <h3 className="mb-2 text-lg font-semibold text-text-primary">{feature.title}</h3>
                <p className="text-sm text-text-secondary">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-4 text-3xl font-bold text-text-primary">
            Ready to find your viral clips?
          </h2>
          <p className="mb-8 text-text-secondary">
            Start with 10 free analyses. No credit card required.
          </p>
          <Link
            to="/dashboard"
            className="inline-block rounded-xl bg-primary px-8 py-4 text-lg font-semibold text-white hover:bg-primary-hover transition-all"
          >
            Start Analyzing
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border px-4 py-8">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center gap-2">
            <LogoIcon className="h-6 w-6" />
            <span className="text-sm text-text-muted">OpenClipPro</span>
          </div>
          <div className="flex gap-6 text-sm text-text-muted">
            <Link to="/about" className="hover:text-text-primary">About</Link>
            <Link to="/pricing" className="hover:text-text-primary">Pricing</Link>
            <a href="https://github.com/zaghl0ul/OpenClipPro" target="_blank" rel="noopener noreferrer" className="hover:text-text-primary">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
