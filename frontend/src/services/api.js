const API_BASE = "/api/v1";

/**
 * Turns an error body into a user-facing message. FastAPI returns `detail`
 * as a string for our own errors but as a list of objects for request
 * validation (422) - never show raw objects or internals to the user.
 */
export function extractErrorMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (status === 422) return "Please check your input and try again.";
  if (status >= 500) return "The AI service is temporarily unavailable.";
  return "Something went wrong. Please try again.";
}

/**
 * Calls the summarization endpoint.
 * Throws an Error with a user-friendly `.message` on failure.
 */
export async function summarizeArticle({ article, url, summaryLength }) {
  let response;
  try {
    response = await fetch(`${API_BASE}/summarize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        article: article || undefined,
        url: url || undefined,
        summary_length: summaryLength,
      }),
    });
  } catch (networkError) {
    throw new Error(
      "Could not reach the server. Make sure the backend is running."
    );
  }

  let body;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    throw new Error(extractErrorMessage(body, response.status));
  }

  return body;
}
