import { useCallback, useRef, useState } from "react";
import { summarizeArticle } from "../services/api";

export const STAGES = [
  { key: "received", label: "Article received" },
  { key: "analyzing", label: "Analyzing article" },
  { key: "sections", label: "Processing sections" },
  { key: "insights", label: "Extracting insights" },
  { key: "synthesizing", label: "Synthesizing summary" },
  { key: "quality", label: "Checking quality" },
  { key: "writing", label: "Generating final summary" },
];

// The backend runs the pipeline in one request, so the frontend can't get
// real per-stage events without adding streaming to the API. Instead we
// advance a proof-sheet of stages on an estimated schedule while the
// request is in flight, and snap to "done" the instant the response lands.
const STAGE_INTERVAL_MS = 900;

export function useSummarizePipeline() {
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [activeStageIndex, setActiveStageIndex] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const clearTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const run = useCallback(async ({ article, url, summaryLength }) => {
    clearTimer();
    setStatus("running");
    setError(null);
    setResult(null);
    setActiveStageIndex(0);

    let stageIndex = 0;
    timerRef.current = setInterval(() => {
      stageIndex = Math.min(stageIndex + 1, STAGES.length - 1);
      setActiveStageIndex(stageIndex);
    }, STAGE_INTERVAL_MS);

    try {
      const data = await summarizeArticle({ article, url, summaryLength });
      clearTimer();
      setActiveStageIndex(STAGES.length - 1);
      setResult(data);
      setStatus("done");
    } catch (err) {
      clearTimer();
      setError(err.message || "Something went wrong.");
      setStatus("error");
    }
  }, []);

  const reset = useCallback(() => {
    clearTimer();
    setStatus("idle");
    setActiveStageIndex(-1);
    setResult(null);
    setError(null);
  }, []);

  return { status, activeStageIndex, result, error, run, reset };
}
