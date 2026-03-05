import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { LogoIcon } from './icons/LogoIcon';

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/projects', label: 'Projects' },
  { path: '/quick-analyze', label: 'Quick Analyze' },
  { path: '/history', label: 'History' },
];

export function Header() {
  const { isAuthenticated, profile, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut();
    navigate('/');
  };

  return (
    <header className="glass sticky top-0 z-50 border-b border-border">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to={isAuthenticated ? '/dashboard' : '/'} className="flex items-center gap-2">
          <LogoIcon className="h-8 w-8" />
          <span className="text-lg font-bold text-text-primary">OpenClipPro</span>
        </Link>

        {isAuthenticated && (
          <nav className="hidden items-center gap-1 md:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-theme ${
                  location.pathname === item.path
                    ? 'bg-primary text-white'
                    : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        )}

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <Link
                to="/settings"
                className="rounded-lg px-3 py-2 text-sm text-text-secondary hover:bg-surface-hover"
              >
                Settings
              </Link>
              <div className="flex items-center gap-2">
                <span className="text-sm text-text-muted">
                  {profile?.credits.remaining ?? 0} credits
                </span>
                <button
                  onClick={handleSignOut}
                  className="rounded-lg bg-surface px-3 py-2 text-sm text-text-secondary hover:bg-surface-hover"
                >
                  Sign Out
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/pricing"
                className="rounded-lg px-3 py-2 text-sm text-text-secondary hover:bg-surface-hover"
              >
                Pricing
              </Link>
              <Link
                to="/about"
                className="rounded-lg px-3 py-2 text-sm text-text-secondary hover:bg-surface-hover"
              >
                About
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
