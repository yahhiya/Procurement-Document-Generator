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
  extractError,
  onContinue,
}) {
  const canContinue = Boolean(file) && !extractError && completedSteps >= ANALYSIS_STEPS.length;

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
            {ANALYSIS_STEPS.map((label, i) => (
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
    </section>
  );
}
