export default function PreviewModal({ title, subtitle, body, onClose }) {
  return (
    <div className="sg-modal-backdrop" onClick={onClose}>
      <div
        className="sg-modal-card sg-preview-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sg-preview-modal-header">
          <div>
            <h2 className="sg-modal-title">{title}</h2>
            {subtitle && <p className="sg-preview-modal-subtitle">{subtitle}</p>}
          </div>
          <button
            type="button"
            className="sg-preview-modal-close"
            onClick={onClose}
            aria-label="Close preview"
          >
            ✕
          </button>
        </div>
        <div className="sg-preview-modal-body">
          <pre className="sg-preview-modal-text">{body}</pre>
        </div>
      </div>
    </div>
  );
}
