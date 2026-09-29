/**
 * Shared shapes for the API contract (documented as JSDoc typedefs).
 *
 * @typedef {"short" | "medium" | "detailed"} SummaryLength
 *
 * @typedef {Object} SummaryMetadata
 * @property {number} input_words
 * @property {number} chunk_count
 * @property {boolean} revised
 * @property {number} duration_seconds
 *
 * @typedef {Object} SummaryResult
 * @property {string} title
 * @property {string} summary
 * @property {string[]} key_points
 * @property {string} main_argument
 * @property {string[]} important_facts
 * @property {string} conclusion
 * @property {number} word_count
 * @property {SummaryMetadata} metadata
 *
 * @typedef {Object} SummarizeInput
 * @property {string} [article]
 * @property {string} [url]
 * @property {SummaryLength} summaryLength
 */

export const SUMMARY_LENGTHS = ["short", "medium", "detailed"];
