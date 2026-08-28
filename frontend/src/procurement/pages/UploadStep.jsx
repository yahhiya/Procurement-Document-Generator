import Button from "../components/Button";
import Dropzone from "../components/Dropzone";
import ProcessItem from "../components/ProcessItem";
import TemplateCombobox from "../components/TemplateCombobox";
import { ArrowRightIcon } from "../components/icons";
import { ANALYSIS_STEPS } from "../data/mockData";

export default function UploadStep({
  templates,
  templatesStatus, // "loading" | "ready" | "error"
  templatesError,
  selectedTemplateId,
  onTemplateChange,
  file,
  onFileSelect,
  onFileClear,
  isAnalysing,
  completedSteps, // number of ANALYSIS_STEPS finished, 0..length
  steps = ANALYSIS_STEPS, // demo mode passes its own (differently worded) step list
  extractError,
  onContinue,
  onTryDemo, // omit this prop to hide the demo button entirely
  isDemo = false,
  onAnalyzeDemo, // called from the "ready" screen's Analyze button, demo mode only
  demoTemplatePreview, // { name, preview_text } — demo mode only
  demoRequirementsPreview, // { name, preview_text } — demo mode only
  onOpenPreview, // (kind: "template" | "requirements") => void, demo mode only
  onOpenInfo, // () => void — "what is this tool" explainer, demo mode only
}) {
  const canContinue = Boolean(file) && !extractError && completedSteps >= steps.length;

  // True right after "Try Interactive Demo" attaches the sample file, and
  // before the user clicks "Analyze Document" — the same beat a real user
  // would hit between dropping a file and the extraction call firing,
  // just made explicit instead of instant, so the demo doesn't skip past
  // it into a progress screen with no context.
  const isDemoReady = isDemo && Boolean(file) && !isAnalysing && completedSteps === 0;

  if (file && isDemoReady) {
    return (
      <section className="sg-card">
        <p className="sg-subtitle" style={{ marginTop: 0 }}>
          A sample template and requirements document are attached. Review below, then analyze
          just like you would with your own document.
          {onOpenInfo && (
            <button
              type="button"
              className="sg-info-btn"
              onClick={onOpenInfo}
              aria-label="What is this tool?"
              title="What is this tool?"
            >
              ?
            </button>
          )}
        </p>

        <div className="sg-field">
          <div className="sg-label-row">
            <label className="sg-label">Document template</label>
          </div>
          <button
            type="button"
            className="sg-file-chip sg-file-chip-clickable"
            onClick={() => onOpenPreview?.("template")}
            style={{ width: "100%", textAlign: "left", border: "1px solid var(--sg-border)" }}
          >
            <span className="sg-file-chip-icon">📄</span>
            <span>
              <div className="sg-file-chip-name">{demoTemplatePreview?.name ?? "Demo Sample Contract"}</div>
              <div className="sg-file-chip-meta">Built-in demo template · click to preview</div>
            </span>
          </button>
        </div>

        <div className="sg-card-section">
          <div className="sg-label-row">
            <label className="sg-label">Requirements document</label>
          </div>
          <button
            type="button"
            className="sg-file-chip sg-file-chip-clickable"
            onClick={() => onOpenPreview?.("requirements")}
            style={{ width: "100%", textAlign: "left", border: "1px solid var(--sg-border)" }}
          >
            <span className="sg-file-chip-icon">📄</span>
            <span>
              <div className="sg-file-chip-name">{demoRequirementsPreview?.name ?? file.name}</div>
              <div className="sg-file-chip-meta">47 KB · click to preview</div>
            </span>
          </button>
        </div>

        <div className="sg-btn-row">
          <Button variant="secondary" onClick={onFileClear}>
            ← Back
          </Button>
          <Button variant="primary" onClick={onAnalyzeDemo}>
            Analyze Document <ArrowRightIcon width={16} height={16} />
          </Button>
        </div>
      </section>
    );
  }

  if (file) {
    if (extractError) {
      return (
        <section className="sg-card">
          <p className="sg-subtitle" style={{ marginTop: 0 }}>
            Something went wrong while reading this document.
          </p>
          <p className="sg-helper is-warning">{extractError}</p>
          <div className="sg-btn-row">
            <Button variant="secondary" onClick={onFileClear}>
              ← Back
            </Button>
            <Button variant="primary" onClick={onFileClear}>
              Try a different file
            </Button>
          </div>
        </section>
      );
    }

    return (
      <section className="sg-card">
        <p className="sg-subtitle" style={{ marginTop: 0 }}>
          Extracting information from your document.
        </p>

        <div className="sg-card-section" style={{ marginTop: 0, borderTop: "none", paddingTop: 0 }}>
          <div className="sg-process-list">
            {steps.map((label, i) => (
              <ProcessItem
                key={label}
                label={label}
                status={
                  i < completedSteps ? "done" : i === completedSteps && isAnalysing ? "active" : "pending"
                }
              />
            ))}
          </div>
        </div>

        <div className="sg-btn-row">
          <Button variant="secondary" onClick={onFileClear}>
            ← Back
          </Button>
          <Button variant="primary" disabled={!canContinue} onClick={onContinue}>
            Continue to review <ArrowRightIcon width={16} height={16} />
          </Button>
        </div>
      </section>
    );
  }

  const comboboxOptions = templates.map((t) => ({ id: t.id, label: t.name }));
  const hasNoTemplates = templatesStatus === "ready" && templates.length === 0;

  return (
    <section className="sg-card">
      <p className="sg-subtitle" style={{ marginTop: 0 }}>
        Select a template and upload your requirements.
      </p>

      <div className="sg-field">
        <div className="sg-label-row">
          <label className="sg-label" htmlFor="template">
            Document template
          </label>
        </div>

        {templatesStatus === "loading" && <p className="sg-helper">Loading templates…</p>}

        {templatesStatus === "error" && (
          <p className="sg-helper is-warning">
            Couldn't load templates. {templatesError}
          </p>
        )}

        {templatesStatus === "ready" && hasNoTemplates && (
          <p className="sg-helper is-warning">
            No active templates available. Ask an admin to activate one under Manage Templates.
          </p>
        )}

        {templatesStatus === "ready" && !hasNoTemplates && (
          <>
            <TemplateCombobox
              id="template"
              options={comboboxOptions}
              value={selectedTemplateId}
              onChange={onTemplateChange}
            />
            <p className="sg-helper">{templates.length} templates available</p>
          </>
        )}
      </div>

      <div className="sg-card-section">
        <div className="sg-label-row">
          <label className="sg-label">Requirements document</label>
        </div>
        <Dropzone file={null} onSelect={onFileSelect} onClear={onFileClear} />
      </div>

      <div className="sg-btn-row">
        <Button variant="primary" block disabled>
          Continue to review <ArrowRightIcon width={16} height={16} />
        </Button>
      </div>
      <p className="sg-helper" style={{ textAlign: "center" }}>
        Upload a document to continue.
      </p>

      {onTryDemo && (
        <>
          <div className="sg-divider">
            <span>or</span>
          </div>
          <button type="button" className="sg-demo-btn" onClick={onTryDemo}>
            ⚡ Try Interactive Demo
          </button>
          <p className="sg-helper" style={{ textAlign: "center" }}>
            Explore the full workflow with a sample contract — no upload needed.
          </p>
        </>
      )}
    </section>
  );
}
