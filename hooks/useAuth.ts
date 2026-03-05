/**
 * Authentication Hook
 *
 * Manages Firebase auth state, login/logout, and user profile.
 * Provides reactive auth state to all consuming components.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  signOut as firebaseSignOut,
  User,
} from 'firebase/auth';
import { doc, getDoc, setDoc, serverTimestamp } from 'firebase/firestore';
import { auth, db } from '@/firebase';
import type { UserProfile, SubscriptionTier } from '@/types';

interface AuthState {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  error: string | null;
}

const DEFAULT_PREFERENCES: UserProfile['preferences'] = {
  defaultProvider: 'gemini',
  defaultMode: 'single',
  defaultPlatforms: ['tiktok', 'youtube-shorts', 'instagram-reels'],
  theme: 'dark',
  autoSave: true,
  notifications: true,
};

function createDefaultProfile(user: User, tier: SubscriptionTier = 'free'): UserProfile {
  const now = new Date();
  return {
    uid: user.uid,
    email: user.email || '',
    displayName: user.displayName || user.email?.split('@')[0] || 'User',
    photoURL: user.photoURL || undefined,
    subscription: tier,
    credits: {
      total: tier === 'free' ? 10 : tier === 'pro' ? 100 : 1000,
      used: 0,
      remaining: tier === 'free' ? 10 : tier === 'pro' ? 100 : 1000,
      resetDate: new Date(now.getFullYear(), now.getMonth() + 1, 1),
    },
    preferences: DEFAULT_PREFERENCES,
    createdAt: now,
    lastLoginAt: now,
  };
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    profile: null,
    loading: true,
    error: null,
  });

  // Fetch or create user profile in Firestore
  const loadProfile = useCallback(async (user: User): Promise<UserProfile> => {
    const profileRef = doc(db, 'users', user.uid);
    const snap = await getDoc(profileRef);

    if (snap.exists()) {
      const data = snap.data() as UserProfile;
      // Update last login
      await setDoc(profileRef, { lastLoginAt: serverTimestamp() }, { merge: true });
      return data;
    }

    // Create new profile for first-time users
    const profile = createDefaultProfile(user);
    await setDoc(profileRef, { ...profile, createdAt: serverTimestamp(), lastLoginAt: serverTimestamp() });
    return profile;
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          const profile = await loadProfile(user);
          setState({ user, profile, loading: false, error: null });
        } catch (err) {
          setState({ user, profile: null, loading: false, error: 'Failed to load profile' });
          console.error('Profile load error:', err);
        }
      } else {
        setState({ user: null, profile: null, loading: false, error: null });
      }
    });
    return unsubscribe;
  }, [loadProfile]);

  const signIn = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Sign in failed';
      setState((s) => ({ ...s, loading: false, error: message }));
      throw err;
    }
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      await createUserWithEmailAndPassword(auth, email, password);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Sign up failed';
      setState((s) => ({ ...s, loading: false, error: message }));
      throw err;
    }
  }, []);

  const signInWithGoogle = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Google sign in failed';
      setState((s) => ({ ...s, loading: false, error: message }));
      throw err;
    }
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(auth);
  }, []);

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  return {
    user: state.user,
    profile: state.profile,
    loading: state.loading,
    error: state.error,
    isAuthenticated: !!state.user,
    signIn,
    signUp,
    signInWithGoogle,
    signOut,
    clearError,
  };
}
