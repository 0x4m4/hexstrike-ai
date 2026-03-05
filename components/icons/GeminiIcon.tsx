export function GeminiIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="#4285F4" />
      <path d="M12 6l2.12 4.28L18.4 12l-4.28 2.12L12 18.4l-2.12-4.28L5.6 12l4.28-2.12L12 6z" fill="white" />
    </svg>
  );
}
