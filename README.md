# OpenClipPro

AI-powered video analysis platform for content creators. Identifies viral-worthy moments in videos using multiple AI models, with smart auto-cropping for every social platform.

## Features

- **Multi-AI "Board of Advisors"** - Run Gemini, GPT-4, Claude, and local models simultaneously for consensus-driven clip detection
- **Viral Score Engine** - 5-dimensional scoring: engagement, shareability, retention, trend alignment, plus AI-generated explanations
- **Smart Auto-Crop** - Automatic crop coordinates for TikTok (9:16), YouTube (16:9), Instagram Reels, and more
- **Browser-Based Processing** - FFmpeg WebAssembly for client-side video trimming. No server uploads required
- **Platform Optimization** - AI recommends the best platform for each clip
- **Project Management** - Organize videos with tags, notes, brand guidelines, and full analysis history
- **Privacy First** - Video files stay in your browser. Only metadata goes to AI providers

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, TypeScript, Vite 6 |
| Styling | Tailwind CSS 4, CSS Variables, Glassmorphism |
| Auth & Data | Firebase (Auth, Firestore, Storage) |
| AI Providers | Google Gemini, OpenAI, Anthropic Claude, LM Studio |
| Video Processing | FFmpeg WASM (client-side) |
| Testing | Playwright |
| Deployment | Docker, Nginx, Firebase Hosting |

## Quick Start

```bash
# Clone
git clone https://github.com/zaghl0ul/OpenClipPro.git
cd OpenClipPro

# Install
npm install

# Configure environment
cp .env.development .env.local
# Edit .env.local with your Firebase credentials

# Run
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Environment Variables

```env
# Firebase (required)
VITE_FIREBASE_API_KEY=your-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id

# AI Providers (set in app settings or env)
VITE_GEMINI_API_KEY=
VITE_OPENAI_API_KEY=
VITE_ANTHROPIC_API_KEY=
VITE_LMSTUDIO_ENDPOINT=http://localhost:1234/v1
```

## Project Structure

```
OpenClipPro/
├── components/         # React UI components
│   └── icons/          # SVG icon components
├── hooks/              # Custom React hooks (auth, analysis, debounce)
├── pages/              # Route-level page components
├── services/           # Business logic
│   └── providers/      # AI provider implementations
├── utils/              # Helper utilities
├── public/ffmpeg/      # FFmpeg WASM files
├── tests/              # Playwright E2E tests
├── App.tsx             # Router & layout
├── firebase.ts         # Firebase initialization
├── types.ts            # TypeScript type definitions
├── themes.css          # Light/dark theme CSS variables
└── index.tsx           # Entry point
```

## Architecture

```
┌─────────────────────────────────────────────┐
│                   App.tsx                     │
│         (Router + ThemeProvider)              │
├──────────┬──────────┬───────────┬────────────┤
│ Landing  │Dashboard │ Projects  │  Settings  │
│  Page    │  Page    │  Pages    │   Page     │
├──────────┴──────────┴───────────┴────────────┤
│              Component Layer                  │
│   VideoInput │ ClipCard │ LLMSelector │ ...   │
├──────────────────────────────────────────────┤
│              Service Layer                    │
│   llmService → providers (Gemini/OpenAI/...) │
│   ffmpegService → FFmpeg WASM                │
│   multiLLMService → Board aggregation        │
├──────────────────────────────────────────────┤
│              Data Layer                       │
│   Firebase Auth │ Firestore │ Storage         │
└──────────────────────────────────────────────┘
```

## Analysis Modes

| Mode | Description |
|------|-------------|
| **Single AI** | Fast analysis with one provider |
| **Board of Advisors** | Multiple AIs analyze simultaneously, results aggregated into consensus scores |
| **Quick Scan** | Rapid top-5 clips with best-platform recommendations |

## Deployment

### Docker

```bash
docker-compose up -d
```

### Firebase Hosting

```bash
npm run build:prod
firebase deploy
```

## Testing

```bash
# Run E2E tests
npm test

# Run with UI
npm run test:ui
```

## License

MIT License - see [LICENSE](LICENSE) for details.
