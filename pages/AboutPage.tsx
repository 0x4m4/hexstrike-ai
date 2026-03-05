import { Link } from 'react-router-dom';

export function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl py-12">
      <h1 className="mb-6 text-4xl font-bold text-text-primary">About OpenClipPro</h1>

      <div className="space-y-6 text-text-secondary">
        <p className="text-lg">
          OpenClipPro is a professional-grade AI-powered video analysis platform built for content creators
          who want to maximize their reach across social media platforms.
        </p>

        <section>
          <h2 className="mb-3 text-2xl font-semibold text-text-primary">How It Works</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>Upload a video or paste a YouTube URL</li>
            <li>Choose your AI provider(s) - Gemini, OpenAI, Claude, or local models</li>
            <li>AI analyzes audio, visuals, and engagement patterns</li>
            <li>Get ranked clips with viral scores and platform recommendations</li>
            <li>Export optimized clips for any social platform</li>
          </ol>
        </section>

        <section>
          <h2 className="mb-3 text-2xl font-semibold text-text-primary">Board of Advisors</h2>
          <p>
            Our unique multi-AI analysis mode runs your video through multiple AI models simultaneously.
            Results are aggregated into a consensus score, giving you higher confidence in which clips
            will perform best. When multiple AIs agree on a moment, you know it has strong viral potential.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-2xl font-semibold text-text-primary">Privacy First</h2>
          <p>
            Video processing happens entirely in your browser using FFmpeg WebAssembly.
            Your video files are never uploaded to our servers. AI analysis uses only
            metadata and frames sent directly to your chosen AI provider.
          </p>
        </section>

        <section>
          <h2 className="mb-3 text-2xl font-semibold text-text-primary">Open Source</h2>
          <p>
            OpenClipPro is open source under the MIT License.
            Contributions, bug reports, and feature requests are welcome on{' '}
            <a
              href="https://github.com/zaghl0ul/OpenClipPro"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              GitHub
            </a>.
          </p>
        </section>
      </div>

      <div className="mt-8">
        <Link
          to="/dashboard"
          className="inline-block rounded-xl bg-primary px-8 py-3 font-semibold text-white hover:bg-primary-hover"
        >
          Try It Now
        </Link>
      </div>
    </div>
  );
}
