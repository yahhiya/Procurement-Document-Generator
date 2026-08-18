import { useEffect } from "react";
import Button from "./Button";

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  tone = "default", // "default" | "danger"
  onConfirm,
  onCancel,
  isBusy = false,
}) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e) => {
      if (e.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="sg-modal-backdrop" onMouseDown={onCancel}>
      <div
        className="sg-modal-card"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="sg-confirm-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <h2 id="sg-confirm-title" className="sg-modal-title">
          {title}
        </h2>
        <p className="sg-modal-description">{description}</p>
        <div className="sg-btn-row" style={{ marginTop: "var(--sg-space-6)" }}>
          <Button variant="secondary" onClick={onCancel} disabled={isBusy}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "danger" : "primary"}
            onClick={onConfirm}
            disabled={isBusy}
          >
            {isBusy ? "Please wait…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
