import Button from "../components/Button";
import { CheckIcon, DownloadIcon, ArrowLeftIcon } from "../components/icons";
import ProcessItem from "../components/ProcessItem";
import { formatFileSize } from "../lib/formatFileSize";

export default function GenerateStep({
  isGenerating,
  generateError,
  generatedFile, // { name, size } once real generation succeeds
  onBackToReview,
  onStartNew,
  onDownload,
}) {
  if (isGenerating) {
    return (
      <section className="sg-card">
        <p className="sg-subtitle" style={{ marginTop: 0 }}>
          Populating the template with confirmed fields.
        </p>
        <div className="sg-process-list">
          <ProcessItem label="Applying confirmed fields" status="done" />
          <ProcessItem label="Formatting document" status="active" />
          <ProcessItem label="Finalising file" status="pending" />
        </div>
      </section>
    );
  }

  if (generateError) {
    return (
      <section className="sg-card">
        <p className="sg-subtitle" style={{ marginTop: 0 }}>
          Something went wrong while generating this document.
        </p>
        <p className="sg-helper is-warning">{generateError}</p>
        <div className="sg-btn-row">
          <Button variant="secondary" onClick={onBackToReview}>
            <ArrowLeftIcon width={16} height={16} /> Back to review
          </Button>
          <Button variant="primary" onClick={onBackToReview}>
            Try again
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section className="sg-card">
      <div className="sg-result">
        <div className="sg-result-icon">
          <CheckIcon width={26} height={26} />
        </div>
        <h2 className="sg-result-title">Document ready</h2>
        <p className="sg-result-subtitle">Generated from the confirmed fields.</p>

        <div className="sg-result-file">
          <span className="sg-file-chip-icon" style={{ background: "var(--sg-success-050)", color: "var(--sg-success-600)" }}>
            <CheckIcon width={18} height={18} />
          </span>
          <span style={{ flex: 1 }}>
            <div className="sg-file-chip-name">{generatedFile?.name}</div>
            <div className="sg-file-chip-meta">
              DOCX file · {generatedFile ? formatFileSize(generatedFile.size) : ""}
            </div>
          </span>
          <span className="sg-badge sg-badge-success">Ready</span>
        </div>

        <Button variant="primary" block onClick={onDownload}>
          <DownloadIcon width={16} height={16} />
          Download document
        </Button>
      </div>

      <div className="sg-btn-row">
        <Button variant="secondary" onClick={onBackToReview}>
          <ArrowLeftIcon width={16} height={16} /> Back to review
        </Button>
        <Button variant="secondary" onClick={onStartNew}>
          Start new document
        </Button>
      </div>
    </section>
  );
}
