// Templates come from the backend (api/templatesApi.js), extracted field
// values come from real AI extraction (api/documentsApi.js), and generated
// documents come from real document generation (api/documentsApi.js).
// This file just holds the one remaining bit of cosmetic UI: the checklist
// shown on the Upload step while a real extraction request is in flight.

export const ANALYSIS_STEPS = [
  "Reading document",
  "Preparing document content",
  "Extracting supplier information",
  "Mapping fields to template",
];

// Shown during the "Try Interactive Demo" loading state instead of the
// steps above. Field values themselves are real, pre-staged sample data
// from the backend (see api/documentsApi.js getDemoSample) — this array is
// purely cosmetic, giving the demo the same "actively working" feel as a
// real extraction without waiting on one.
export const DEMO_ANALYSIS_STEPS = [
  "Loading sample contract…",
  "Analyzing requirements…",
  "Extracting fields…",
  "Mapping fields to template…",
];
