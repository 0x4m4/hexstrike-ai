/**
 * OpenClipPro - Core Type Definitions
 *
 * Comprehensive domain model for AI-powered video analysis,
 * viral scoring, multi-LLM support, and project management.
 */

// ============================================================================
// AI Provider Types
// ============================================================================

export type AIProvider = 'gemini' | 'openai' | 'anthropic' | 'lmstudio';

export interface AIProviderConfig {
  provider: AIProvider;
  apiKey: string;
  model: string;
  endpoint?: string; // For LM Studio custom endpoints
  maxTokens?: number;
  temperature?: number;
}

export interface ProviderStatus {
  provider: AIProvider;
  isConfigured: boolean;
  isAvailable: boolean;
  lastChecked: Date | null;
  error?: string;
}

// ============================================================================
// Viral Score System
// ============================================================================

export interface ViralScoreBreakdown {
  overall: number;        // 0-100
  engagement: number;     // 0-100 - How likely viewers will interact
  shareability: number;   // 0-100 - How likely to be shared
  retention: number;      // 0-100 - How well it keeps attention
  trendAlignment: number; // 0-100 - How well it fits current trends
  explanation: string;    // AI-generated reasoning
}

// ============================================================================
// Audio & Visual Analysis
// ============================================================================

export interface AudioAnalysis {
  musicIntensity: number;    // 0-1
  speechCoverage: number;    // 0-1
  emotionalPeaks: number[];  // Timestamps of emotional peaks
  volumeDynamics: number[];  // Volume levels over time
  tempo: number;             // BPM estimate
  hasSpeech: boolean;
  hasMusic: boolean;
}

export type MomentType = 'emotional-peak' | 'action' | 'transition' | 'speech' | 'visual-hook';

export interface KeyMoment {
  timestamp: number;
  type: MomentType;
  confidence: number;
  description: string;
}

// ============================================================================
// Aspect Ratio & Cropping
// ============================================================================

export type AspectRatio = '16:9' | '9:16' | '1:1';

export interface CropCoordinates {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type CropMap = Record<AspectRatio, CropCoordinates>;

// ============================================================================
// Platform Configuration
// ============================================================================

export type Platform = 'tiktok' | 'youtube-shorts' | 'instagram-reels' | 'youtube' | 'twitter';

export interface PlatformConfig {
  platform: Platform;
  aspectRatio: AspectRatio;
  maxDuration: number;    // seconds
  minDuration: number;    // seconds
  label: string;
  icon: string;
}

export const PLATFORM_CONFIGS: Record<Platform, PlatformConfig> = {
  'tiktok': {
    platform: 'tiktok',
    aspectRatio: '9:16',
    maxDuration: 180,
    minDuration: 5,
    label: 'TikTok',
    icon: '🎵',
  },
  'youtube-shorts': {
    platform: 'youtube-shorts',
    aspectRatio: '9:16',
    maxDuration: 60,
    minDuration: 15,
    label: 'YouTube Shorts',
    icon: '📱',
  },
  'instagram-reels': {
    platform: 'instagram-reels',
    aspectRatio: '9:16',
    maxDuration: 90,
    minDuration: 5,
    label: 'Instagram Reels',
    icon: '📸',
  },
  'youtube': {
    platform: 'youtube',
    aspectRatio: '16:9',
    maxDuration: 600,
    minDuration: 30,
    label: 'YouTube',
    icon: '▶️',
  },
  'twitter': {
    platform: 'twitter',
    aspectRatio: '16:9',
    maxDuration: 140,
    minDuration: 5,
    label: 'Twitter/X',
    icon: '🐦',
  },
};

// ============================================================================
// Clip Types
// ============================================================================

export interface Clip {
  id: string;
  title: string;
  description: string;
  startTime: number;
  endTime: number;
  duration: number;
  viralScore: ViralScoreBreakdown;
  audioAnalysis: AudioAnalysis;
  keyMoments: KeyMoment[];
  cropCoordinates: CropMap;
  bestPlatform: Platform;
  tags: string[];
  transcript?: string;
  thumbnailUrl?: string;
  videoUrl?: string;
  generatedClips?: GeneratedClip[];
}

export interface GeneratedClip {
  id: string;
  clipId: string;
  platform: Platform;
  aspectRatio: AspectRatio;
  blobUrl: string;
  fileSize: number;
  duration: number;
  createdAt: Date;
}

// ============================================================================
// Multi-LLM Analysis
// ============================================================================

export type AnalysisMode = 'single' | 'board' | 'quick';

export interface ProviderAnalysis {
  provider: AIProvider;
  clips: Clip[];
  confidence: number;
  processingTime: number;
  model: string;
  error?: string;
}

export interface AggregatedClip extends Clip {
  confidenceScore: number;       // 0-1, consensus confidence
  providerAgreement: number;     // How many providers agreed
  providerVariations: {
    provider: AIProvider;
    viralScore: number;
    startTimeDiff: number;
    endTimeDiff: number;
  }[];
  consensusNotes: string;
}

export interface MultiLLMAnalysisResult {
  mode: AnalysisMode;
  providers: ProviderAnalysis[];
  aggregatedClips: AggregatedClip[];
  totalProcessingTime: number;
  timestamp: Date;
  videoId: string;
}

// ============================================================================
// Quick Analysis
// ============================================================================

export interface QuickAnalysisResult {
  clips: Clip[];
  confidence: number;
  processingTime: number;
  provider: AIProvider;
  model: string;
}

// ============================================================================
// Project Management
// ============================================================================

export type ProjectStatus = 'draft' | 'analyzing' | 'completed' | 'archived';

export interface ProjectSettings {
  targetPlatforms: Platform[];
  analysisMode: AnalysisMode;
  providers: AIProvider[];
  maxClips: number;
  minViralScore: number;
  language: string;
  brandGuidelines?: string;
}

export interface ProjectStats {
  totalClips: number;
  averageViralScore: number;
  topPlatform: Platform | null;
  analysisCount: number;
  lastAnalyzedAt: Date | null;
}

export interface Project {
  id: string;
  userId: string;
  name: string;
  description: string;
  status: ProjectStatus;
  settings: ProjectSettings;
  stats: ProjectStats;
  tags: string[];
  collaborators: string[];
  videoUrl?: string;
  videoFileName?: string;
  videoDuration?: number;
  thumbnailUrl?: string;
  clips: Clip[];
  analyses: MultiLLMAnalysisResult[];
  createdAt: Date;
  updatedAt: Date;
}

// ============================================================================
// User & Subscription
// ============================================================================

export type SubscriptionTier = 'free' | 'pro' | 'enterprise';

export interface UserCredits {
  total: number;
  used: number;
  remaining: number;
  resetDate: Date;
}

export interface UserPreferences {
  defaultProvider: AIProvider;
  defaultMode: AnalysisMode;
  defaultPlatforms: Platform[];
  theme: 'light' | 'dark' | 'system';
  autoSave: boolean;
  notifications: boolean;
}

export interface UserProfile {
  uid: string;
  email: string;
  displayName: string;
  photoURL?: string;
  subscription: SubscriptionTier;
  credits: UserCredits;
  preferences: UserPreferences;
  createdAt: Date;
  lastLoginAt: Date;
}

// ============================================================================
// Analysis Configuration
// ============================================================================

export interface AnalysisConfig {
  mode: AnalysisMode;
  providers: AIProviderConfig[];
  targetPlatforms: Platform[];
  maxClips: number;
  minDuration: number;
  maxDuration: number;
  minViralScore: number;
  language: string;
  includeTranscript: boolean;
  includeAudioAnalysis: boolean;
}

// ============================================================================
// UI State Types
// ============================================================================

export interface AnalysisProgress {
  stage: 'uploading' | 'extracting' | 'analyzing' | 'scoring' | 'cropping' | 'complete' | 'error';
  progress: number; // 0-100
  message: string;
  provider?: AIProvider;
}

export interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
}

export interface VideoInputSource {
  type: 'file' | 'youtube' | 'url';
  value: string | File;
  fileName?: string;
  duration?: number;
  thumbnailUrl?: string;
}
