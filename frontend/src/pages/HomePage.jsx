import React from "react";
import ArticleInput from "../components/ArticleInput";
import PipelineProgress from "../components/PipelineProgress";
import ResultDisplay from "../components/ResultDisplay";
import { useSummarizePipeline } from "../hooks/useSummarizePipeline";

export default function HomePage() {
  const { status, activeStageIndex, result, error, run, reset } =
    useSummarizePipeline();
  const isRunning = status === "running";

  return (
    <div className="app-shell">
      <header className="masthead">
        <h1 className="masthead-title">AI Article Summarizer</h1>
        <p className="masthead-subtitle">
          Transform long articles into structured, grounded summaries.
        </p>
      </header>

      <main className="workspace">
        <section className="desk">
          <ArticleInput onSubmit={run} disabled={isRunning} />

          {status === "error" && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}

          {(isRunning || status === "done") && (
            <PipelineProgress activeStageIndex={activeStageIndex} status={status} />
          )}
        </section>

        <section className="reading-pane" aria-live="polite">
          <ResultDisplay result={status === "done" ? result : null} onReset={reset} />
        </section>
      </main>
    </div>
  );
}
