import React from "react";
import { STAGES } from "../hooks/useSummarizePipeline";

export default function PipelineProgress({ activeStageIndex, status }) {
  return (
    <div className="proof-sheet">
      <p className="proof-title">PIPELINE STATUS</p>
      {STAGES.map((stage, index) => {
        const isDone =
          index < activeStageIndex || (status === "done" && index <= activeStageIndex);
        const isActive = index === activeStageIndex && status === "running";
        const className =
          "proof-stage" + (isDone ? " done" : "") + (isActive ? " active" : "");
        return (
          <div key={stage.key} className={className}>
            <span className="proof-mark">
              {isDone ? "✓" : isActive ? "…" : "·"}
            </span>
            <span>{stage.label}</span>
          </div>
        );
      })}
    </div>
  );
}
