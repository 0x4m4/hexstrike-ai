import { useRef, useState, useEffect, useCallback } from 'react';
import { formatTimestamp } from '@/utils/performance';

interface ClipPreviewProps {
  src: string;
  startTime: number;
  endTime: number;
  onStartTimeChange?: (time: number) => void;
  onEndTimeChange?: (time: number) => void;
  duration: number;
}

export function ClipPreview({
  src,
  startTime,
  endTime,
  onStartTimeChange,
  onEndTimeChange,
  duration,
}: ClipPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(startTime);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      if (video.currentTime >= endTime) {
        video.pause();
        video.currentTime = startTime;
        setIsPlaying(false);
      }
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [startTime, endTime]);

  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
      setIsPlaying(false);
    } else {
      if (video.currentTime < startTime || video.currentTime >= endTime) {
        video.currentTime = startTime;
      }
      video.play();
      setIsPlaying(true);
    }
  }, [isPlaying, startTime, endTime]);

  const seekTo = useCallback((time: number) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = time;
    setCurrentTime(time);
  }, []);

  const clipProgress = duration > 0
    ? ((currentTime - startTime) / (endTime - startTime)) * 100
    : 0;

  return (
    <div className="glass rounded-xl overflow-hidden">
      {/* Video Player */}
      <div className="relative bg-black">
        <video
          ref={videoRef}
          src={src}
          className="w-full aspect-video"
          onClick={togglePlay}
        />
        <button
          onClick={togglePlay}
          className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity hover:opacity-100"
        >
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
            <span className="text-2xl text-white">
              {isPlaying ? '⏸' : '▶'}
            </span>
          </div>
        </button>

        {/* Time Overlay */}
        <div className="absolute bottom-2 left-2 rounded bg-black/60 px-2 py-1 text-xs text-white">
          {formatTimestamp(currentTime)} / {formatTimestamp(duration)}
        </div>
      </div>

      {/* Timeline Scrubber */}
      <div className="p-4">
        <div className="relative mb-3">
          {/* Full timeline */}
          <div className="h-8 rounded bg-surface relative cursor-pointer"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const pct = (e.clientX - rect.left) / rect.width;
              seekTo(pct * duration);
            }}
          >
            {/* Selected region */}
            <div
              className="absolute top-0 h-full rounded bg-primary/20"
              style={{
                left: `${(startTime / duration) * 100}%`,
                width: `${((endTime - startTime) / duration) * 100}%`,
              }}
            />
            {/* Playhead */}
            <div
              className="absolute top-0 h-full w-0.5 bg-white"
              style={{ left: `${(currentTime / duration) * 100}%` }}
            />
            {/* Start marker */}
            {onStartTimeChange && (
              <div
                className="absolute top-0 h-full w-1 cursor-ew-resize bg-green-400"
                style={{ left: `${(startTime / duration) * 100}%` }}
                onMouseDown={(e) => {
                  e.preventDefault();
                  const bar = e.currentTarget.parentElement!;
                  const onMove = (ev: MouseEvent) => {
                    const rect = bar.getBoundingClientRect();
                    const pct = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
                    const time = pct * duration;
                    if (time < endTime - 1) onStartTimeChange(time);
                  };
                  const onUp = () => {
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup', onUp);
                  };
                  document.addEventListener('mousemove', onMove);
                  document.addEventListener('mouseup', onUp);
                }}
              />
            )}
            {/* End marker */}
            {onEndTimeChange && (
              <div
                className="absolute top-0 h-full w-1 cursor-ew-resize bg-red-400"
                style={{ left: `${(endTime / duration) * 100}%` }}
                onMouseDown={(e) => {
                  e.preventDefault();
                  const bar = e.currentTarget.parentElement!;
                  const onMove = (ev: MouseEvent) => {
                    const rect = bar.getBoundingClientRect();
                    const pct = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
                    const time = pct * duration;
                    if (time > startTime + 1) onEndTimeChange(time);
                  };
                  const onUp = () => {
                    document.removeEventListener('mousemove', onMove);
                    document.removeEventListener('mouseup', onUp);
                  };
                  document.addEventListener('mousemove', onMove);
                  document.addEventListener('mouseup', onUp);
                }}
              />
            )}
          </div>
        </div>

        {/* Clip Progress */}
        <div className="h-1 rounded-full bg-surface overflow-hidden">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${Math.max(0, Math.min(100, clipProgress))}%` }}
          />
        </div>

        {/* Time Labels */}
        <div className="mt-2 flex justify-between text-xs text-text-muted">
          <span className="text-green-400">In: {formatTimestamp(startTime)}</span>
          <span>{(endTime - startTime).toFixed(1)}s</span>
          <span className="text-red-400">Out: {formatTimestamp(endTime)}</span>
        </div>
      </div>
    </div>
  );
}
