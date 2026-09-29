import React, { useMemo, useState } from "react";

const LENGTH_OPTIONS = [
  { value: "short", name: "Short", hint: "100-150 words" },
  { value: "medium", name: "Medium", hint: "250-350 words" },
  { value: "detailed", name: "Detailed", hint: "450-600 words" },
];

export default function ArticleInput({ onSubmit, disabled }) {
  const [article, setArticle] = useState("");
  const [url, setUrl] = useState("");
  const [summaryLength, setSummaryLength] = useState("medium");
  const [validationError, setValidationError] = useState(null);

  const wordCount = useMemo(
    () => (article.trim() ? article.trim().split(/\s+/).length : 0),
    [article]
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!article.trim() && !url.trim()) {
      setValidationError("Please enter an article or a URL.");
      return;
    }
    setValidationError(null);
    onSubmit({ article: article.trim(), url: url.trim(), summaryLength });
  };

  return (
    <form onSubmit={handleSubmit}>
      <div style={{ marginBottom: "1.1rem" }}>
        <label className="field-label" htmlFor="article-text">
          Article text
        </label>
        <textarea
          id="article-text"
          className="article-textarea"
          placeholder="Paste the full article here..."
          value={article}
          onChange={(e) => setArticle(e.target.value)}
          disabled={disabled}
        />
        <div className="word-count">{wordCount} words</div>
      </div>

      <div style={{ marginBottom: "1.1rem" }}>
        <label className="field-label" htmlFor="article-url">
          Or a URL (optional)
        </label>
        <input
          id="article-url"
          className="url-input"
          type="text"
          placeholder="https://example.com/article"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={disabled}
        />
      </div>

      <div style={{ marginBottom: "1.1rem" }}>
        <label className="field-label">Summary length</label>
        <div className="length-row">
          {LENGTH_OPTIONS.map((opt) => (
            <button
              type="button"
              key={opt.value}
              className={
                "length-option" + (summaryLength === opt.value ? " active" : "")
              }
              onClick={() => setSummaryLength(opt.value)}
              disabled={disabled}
            >
              <span className="length-option-name">{opt.name}</span>
              {opt.hint}
            </button>
          ))}
        </div>
      </div>

      {validationError && (
        <div className="error-banner" style={{ marginBottom: "1rem" }}>
          {validationError}
        </div>
      )}

      <button type="submit" className="generate-button" disabled={disabled}>
        {disabled ? "Working..." : "Generate Summary"}
      </button>
    </form>
  );
}
