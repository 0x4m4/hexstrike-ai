/**
 * UI Test Component
 *
 * Development-only page for testing all UI components
 * and theme variables in one place.
 */

export function UITest() {
  if (import.meta.env.PROD) return null;

  return (
    <div className="space-y-8 p-6">
      <h1 className="text-3xl font-bold text-text-primary">UI Component Test</h1>

      {/* Colors */}
      <section>
        <h2 className="mb-3 text-xl font-semibold text-text-primary">Colors</h2>
        <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
          {[
            ['Primary', 'bg-primary'],
            ['Primary Hover', 'bg-primary-hover'],
            ['Secondary', 'bg-secondary'],
            ['Accent', 'bg-accent'],
            ['Background', 'bg-background border border-border'],
            ['Surface', 'bg-surface'],
            ['Success', 'bg-success'],
            ['Warning', 'bg-warning'],
            ['Error', 'bg-error'],
            ['Info', 'bg-info'],
          ].map(([label, cls]) => (
            <div key={label} className="text-center">
              <div className={`h-12 rounded-lg ${cls}`} />
              <div className="mt-1 text-xs text-text-muted">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Typography */}
      <section>
        <h2 className="mb-3 text-xl font-semibold text-text-primary">Typography</h2>
        <div className="space-y-2">
          <p className="text-text-primary">text-text-primary - Main content text</p>
          <p className="text-text-secondary">text-text-secondary - Secondary text</p>
          <p className="text-text-muted">text-text-muted - Muted/disabled text</p>
        </div>
      </section>

      {/* Buttons */}
      <section>
        <h2 className="mb-3 text-xl font-semibold text-text-primary">Buttons</h2>
        <div className="flex flex-wrap gap-3">
          <button className="rounded-lg bg-primary px-4 py-2 text-white hover:bg-primary-hover">
            Primary
          </button>
          <button className="rounded-lg bg-surface px-4 py-2 text-text-primary hover:bg-surface-hover">
            Surface
          </button>
          <button className="rounded-lg border border-border px-4 py-2 text-text-secondary hover:bg-surface">
            Outlined
          </button>
          <button className="rounded-lg bg-primary px-4 py-2 text-white opacity-50" disabled>
            Disabled
          </button>
        </div>
      </section>

      {/* Glass Cards */}
      <section>
        <h2 className="mb-3 text-xl font-semibold text-text-primary">Glass Cards</h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="glass rounded-xl p-4">
            <h3 className="font-semibold text-text-primary">Default Glass</h3>
            <p className="text-sm text-text-secondary">Standard glassmorphism card</p>
          </div>
          <div className="glass rounded-xl p-4 shadow-card">
            <h3 className="font-semibold text-text-primary">Shadow Card</h3>
            <p className="text-sm text-text-secondary">With card shadow</p>
          </div>
          <div className="glass rounded-xl p-4 shadow-elevated">
            <h3 className="font-semibold text-text-primary">Elevated</h3>
            <p className="text-sm text-text-secondary">With elevated shadow</p>
          </div>
        </div>
      </section>

      {/* Inputs */}
      <section>
        <h2 className="mb-3 text-xl font-semibold text-text-primary">Inputs</h2>
        <div className="max-w-md space-y-3">
          <input
            type="text"
            placeholder="Default input"
            className="w-full rounded-lg border border-border bg-surface px-4 py-2 text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none"
          />
          <select className="w-full rounded-lg border border-border bg-surface px-4 py-2 text-text-primary focus:border-primary focus:outline-none">
            <option>Select option</option>
            <option>Option A</option>
            <option>Option B</option>
          </select>
        </div>
      </section>
    </div>
  );
}
