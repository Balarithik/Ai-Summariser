import React, { useState } from "react";

function useCopy() {
  const [copiedKey, setCopiedKey] = useState(null);
  const copy = async (key, text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey((k) => (k === key ? null : k)), 1500);
    } catch {
      // Clipboard access can fail (permissions, insecure context) - fail silently,
      // the user can still select and copy manually.
    }
  };
  return { copiedKey, copy };
}

function buildFullText(result) {
  return [
    result.title,
    "",
    result.summary,
    "",
    "KEY POINTS",
    ...result.key_points.map((p) => `- ${p}`),
    "",
    "MAIN ARGUMENT",
    result.main_argument,
    "",
    "IMPORTANT FACTS",
    ...result.important_facts.map((f) => `- ${f}`),
    "",
    "CONCLUSION",
    result.conclusion,
  ].join("\n");
}

export default function ResultDisplay({ result, onReset }) {
  const { copiedKey, copy } = useCopy();

  if (!result) {
    return (
      <p className="reading-empty">
        Paste an article on the left and its structured summary will take
        shape here.
      </p>
    );
  }

  const { metadata } = result;

  return (
    <div>
      <p className="result-kicker">EXECUTIVE SUMMARY</p>
      <h1 className="result-title">{result.title}</h1>

      <div className="result-actions">
        <button
          className="action-button"
          onClick={() => copy("summary", result.summary)}
        >
          {copiedKey === "summary" ? "Copied" : "Copy summary"}
        </button>
        <button
          className="action-button"
          onClick={() => copy("all", buildFullText(result))}
        >
          {copiedKey === "all" ? "Copied" : "Copy all"}
        </button>
        <button className="action-button" onClick={onReset}>
          New article
        </button>
      </div>

      {metadata?.revised && (
        <div className="revision-note">Refined after an internal quality check</div>
      )}

      <p className="result-summary">{result.summary}</p>

      {result.key_points?.length > 0 && (
        <div className="result-section">
          <p className="result-section-heading">KEY POINTS</p>
          <ul className="result-list">
            {result.key_points.map((point, i) => (
              <li key={i}>{point}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="result-section">
        <p className="result-section-heading">MAIN ARGUMENT</p>
        <p className="result-prose">{result.main_argument}</p>
      </div>

      {result.important_facts?.length > 0 && (
        <div className="result-section">
          <p className="result-section-heading">IMPORTANT FACTS</p>
          <ul className="result-list">
            {result.important_facts.map((fact, i) => (
              <li key={i}>{fact}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="result-section">
        <p className="result-section-heading">CONCLUSION</p>
        <p className="result-prose">{result.conclusion}</p>
      </div>

      {metadata && (
        <div className="result-meta-strip">
          <span>
            <strong>{metadata.input_words}</strong> input words
          </span>
          <span>
            <strong>{metadata.chunk_count}</strong> sections processed
          </span>
          <span>
            <strong>{result.word_count}</strong> word summary
          </span>
          <span>
            <strong>{metadata.duration_seconds}s</strong> generation time
          </span>
        </div>
      )}
    </div>
  );
}
