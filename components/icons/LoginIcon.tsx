export function LoginIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points="10 17 15 12 10 7" strokeLinecap="round" strokeLinejoin="round" />
      <line x1="15" y1="12" x2="3" y2="12" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
