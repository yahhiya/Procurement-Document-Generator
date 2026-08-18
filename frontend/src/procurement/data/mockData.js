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
