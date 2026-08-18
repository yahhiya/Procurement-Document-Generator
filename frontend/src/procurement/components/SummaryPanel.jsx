function Row({ label, value, muted = false }) {
  return (
    <div className="sg-summary-row">
      <span className="sg-summary-label">{label}</span>
      <span className={`sg-summary-value ${muted ? "is-muted" : ""}`}>
        {value ?? "—"}
      </span>
    </div>
  );
}

export default function SummaryPanel({ template, file, status }) {
  return (
    <aside className="sg-summary" aria-label="Document summary">
      <p className="sg-summary-title">Document summary</p>
      <Row label="Template" value={template} muted={!template} />
      <Row label="Source file" value={file} muted={!file} />
      <Row label="Status" value={status} />
      <p className="sg-summary-footnote">Updates as you progress.</p>
    </aside>
  );
}
