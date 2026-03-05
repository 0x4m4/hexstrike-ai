import { useEffect, useCallback } from 'react';
import type { AIProvider } from '@/types';

const STORAGE_KEY = 'openclippro-api-keys';

interface ApiKeyLoaderProps {
  onKeysLoaded: (keys: Record<AIProvider, string>) => void;
}

export function ApiKeyLoader({ onKeysLoaded }: ApiKeyLoaderProps) {
  useEffect(() => {
    const keys = loadApiKeys();
    onKeysLoaded(keys);
  }, [onKeysLoaded]);

  return null; // Invisible component
}

export function loadApiKeys(): Record<AIProvider, string> {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch { /* ignore */ }

  return {
    gemini: import.meta.env.VITE_GEMINI_API_KEY || '',
    openai: import.meta.env.VITE_OPENAI_API_KEY || '',
    anthropic: import.meta.env.VITE_ANTHROPIC_API_KEY || '',
    lmstudio: '',
  };
}

export function saveApiKeys(keys: Record<AIProvider, string>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(keys));
  } catch { /* ignore */ }
}

export function usePersistentApiKeys(
  keys: Record<AIProvider, string>,
  setKeys: (keys: Record<AIProvider, string>) => void
) {
  // Load on mount
  useEffect(() => {
    const loaded = loadApiKeys();
    setKeys(loaded);
  }, [setKeys]);

  // Save on change
  const updateKey = useCallback(
    (provider: AIProvider, key: string) => {
      const updated = { ...keys, [provider]: key };
      setKeys(updated);
      saveApiKeys(updated);
    },
    [keys, setKeys]
  );

  return { updateKey };
}
