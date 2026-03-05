export function LogoIcon({ className = 'h-8 w-8' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="12" fill="url(#logo-gradient)" />
      <path
        d="M14 18L22 12L30 18V30L22 36L14 30V18Z"
        stroke="white"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path d="M22 12V36" stroke="white" strokeWidth="1.5" opacity="0.5" />
      <path d="M14 18L30 30" stroke="white" strokeWidth="1.5" opacity="0.5" />
      <path d="M30 18L14 30" stroke="white" strokeWidth="1.5" opacity="0.5" />
      <circle cx="34" cy="14" r="6" fill="white" fillOpacity="0.9" />
      <path d="M32 14L33.5 15.5L36.5 12.5" stroke="url(#logo-gradient)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <defs>
        <linearGradient id="logo-gradient" x1="0" y1="0" x2="48" y2="48">
          <stop stopColor="#6366f1" />
          <stop offset="1" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
    </svg>
  );
}
