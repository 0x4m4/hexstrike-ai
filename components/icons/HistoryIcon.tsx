export function HistoryIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path d="M12 8v4l3 3" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h1M20 12h1" strokeLinecap="round" />
    </svg>
  );
}
