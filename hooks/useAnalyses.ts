/**
 * Analysis State Hook
 *
 * Manages the lifecycle of video analysis operations:
 * progress tracking, result storage, and error handling.
 */

import { useState, useCallback } from 'react';
import type {
  AnalysisConfig,
  AnalysisProgress,
  MultiLLMAnalysisResult,
  QuickAnalysisResult,
  VideoInputSource,
} from '@/types';
import { analyzeVideo } from '@/services/llmService';

interface AnalysisState {
  progress: AnalysisProgress | null;
  result: MultiLLMAnalysisResult | QuickAnalysisResult | null;
  isAnalyzing: boolean;
  error: string | null;
}

export function useAnalyses() {
  const [state, setState] = useState<AnalysisState>({
    progress: null,
    result: null,
    isAnalyzing: false,
    error: null,
  });

  const updateProgress = useCallback((progress: AnalysisProgress) => {
    setState((s) => ({ ...s, progress }));
  }, []);

  const startAnalysis = useCallback(
    async (source: VideoInputSource, config: AnalysisConfig) => {
      setState({
        progress: { stage: 'uploading', progress: 0, message: 'Preparing video...' },
        result: null,
        isAnalyzing: true,
        error: null,
      });

      try {
        const result = await analyzeVideo(source, config, updateProgress);
        setState({
          progress: { stage: 'complete', progress: 100, message: 'Analysis complete!' },
          result,
          isAnalyzing: false,
          error: null,
        });
        return result;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Analysis failed';
        setState({
          progress: { stage: 'error', progress: 0, message },
          result: null,
          isAnalyzing: false,
          error: message,
        });
        throw err;
      }
    },
    [updateProgress]
  );

  const reset = useCallback(() => {
    setState({ progress: null, result: null, isAnalyzing: false, error: null });
  }, []);

  return {
    ...state,
    startAnalysis,
    reset,
  };
}
