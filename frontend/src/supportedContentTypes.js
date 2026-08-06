/**
 * User-facing content-search types for Settings / add-folder (#128).
 *
 * Must stay in sync with backend/indexer/extract.py CONTENT_EXTENSIONS
 * (pdf, txt, md, markdown, docx). Collapse md/markdown → "Markdown" here.
 * When adding a parser, update that frozenset and this list together.
 */

/** Display labels for content-extracted formats (not filename-only). */
export const CONTENT_TYPE_LABELS = ['TXT', 'Markdown', 'DOCX', 'PDF']

/** Short standing caption for Settings corpus section. */
export const CONTENT_TYPES_CAPTION =
  `Content search: ${CONTENT_TYPE_LABELS.join(', ')}. Other files: filename only. Hidden folders and common junk dirs are skipped.`
