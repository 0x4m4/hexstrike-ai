import { useState, useRef, useCallback } from 'react';
import type { VideoInputSource } from '@/types';
import { validateVideoFile } from '@/utils/videoProcessor';

interface VideoInputProps {
  onVideoSelected: (source: VideoInputSource) => void;
  disabled?: boolean;
}

type InputTab = 'file' | 'youtube' | 'url';

export function VideoInput({ onVideoSelected, disabled }: VideoInputProps) {
  const [activeTab, setActiveTab] = useState<InputTab>('file');
  const [urlValue, setUrlValue] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      setError(null);
      const validationError = validateVideoFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      onVideoSelected({
        type: 'file',
        value: file,
        fileName: file.name,
      });
    },
    [onVideoSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleUrlSubmit = () => {
    setError(null);
    if (!urlValue.trim()) {
      setError('Please enter a URL');
      return;
    }
    const type = urlValue.includes('youtube.com') || urlValue.includes('youtu.be') ? 'youtube' : 'url';
    onVideoSelected({ type, value: urlValue.trim() });
  };

  const tabs: Array<{ id: InputTab; label: string }> = [
    { id: 'file', label: 'Upload File' },
    { id: 'youtube', label: 'YouTube URL' },
    { id: 'url', label: 'Video URL' },
  ];

  return (
    <div className="glass rounded-xl p-6">
      {/* Tab Switcher */}
      <div className="mb-4 flex gap-1 rounded-lg bg-surface p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id); setError(null); }}
            disabled={disabled}
            className={`flex-1 rounded-md py-2 text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-primary text-white shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* File Upload */}
      {activeTab === 'file' && (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition-all ${
            dragActive
              ? 'border-primary bg-primary/10'
              : 'border-border hover:border-primary/50 hover:bg-surface'
          } ${disabled ? 'pointer-events-none opacity-50' : ''}`}
        >
          <div className="mb-2 text-4xl">🎬</div>
          <p className="mb-1 font-medium text-text-primary">
            {dragActive ? 'Drop your video here' : 'Drag & drop a video or click to browse'}
          </p>
          <p className="text-sm text-text-muted">MP4, WebM, MOV, MKV up to 2GB</p>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>
      )}

      {/* URL Input */}
      {(activeTab === 'youtube' || activeTab === 'url') && (
        <div className="flex gap-2">
          <input
            type="url"
            value={urlValue}
            onChange={(e) => setUrlValue(e.target.value)}
            placeholder={
              activeTab === 'youtube'
                ? 'https://www.youtube.com/watch?v=...'
                : 'https://example.com/video.mp4'
            }
            disabled={disabled}
            className="flex-1 rounded-lg border border-border bg-surface px-4 py-3 text-text-primary placeholder:text-text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            onKeyDown={(e) => e.key === 'Enter' && handleUrlSubmit()}
          />
          <button
            onClick={handleUrlSubmit}
            disabled={disabled || !urlValue.trim()}
            className="rounded-lg bg-primary px-6 py-3 font-medium text-white hover:bg-primary-hover disabled:opacity-50"
          >
            Analyze
          </button>
        </div>
      )}

      {error && (
        <div className="mt-3 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</div>
      )}
    </div>
  );
}
