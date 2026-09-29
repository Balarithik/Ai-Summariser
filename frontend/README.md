# Frontend - AI Article Summarizer

A React + Vite interface for the multi-stage summarization pipeline.

## Setup

```bash
cd frontend
npm install
```

## Run (development)

```bash
npm run dev
```

Opens at `http://localhost:5173`. API requests to `/api/*` are proxied to
the backend at `http://127.0.0.1:8000` (see `vite.config.js`) - make sure
the backend is running first.

## Build for production

```bash
npm run build
npm run preview
```

## Structure

- `src/components/ArticleInput.jsx` - article/URL input, length selector
- `src/components/PipelineProgress.jsx` - live pipeline stage indicator
- `src/components/ResultDisplay.jsx` - structured result reading pane
- `src/hooks/useSummarizePipeline.js` - request lifecycle + stage progress
- `src/services/api.js` - backend API client
