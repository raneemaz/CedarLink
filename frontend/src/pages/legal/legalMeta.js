// The single source of the "last updated" date shown on both legal pages
// (/privacy-policy and /terms). Change it here whenever either document
// changes in substance — never type a date into the translation files or
// the components.
//
// Kept as a plain calendar date for humans to edit; the ISO form pins it
// to noon UTC so the rendered day is identical in every timezone the app
// is read in.
export const LEGAL_LAST_UPDATED = "2026-09-06";

export const LEGAL_LAST_UPDATED_ISO = `${LEGAL_LAST_UPDATED}T12:00:00Z`;
