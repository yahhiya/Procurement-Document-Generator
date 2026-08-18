import { useEffect, useRef, useState } from "react";
import Button from "../components/Button";
import Badge from "../components/Badge";
import { CloseIcon, CheckIcon } from "../components/icons";
import { useAuth } from "../context/AuthContext";
import * as adminApi from "../api/adminApi";

const FIELD_TYPES = ["text", "paragraph", "number", "currency", "date"];
const AUTO_CLOSE_DELAY_MS = 1600;

function slugify(label, usedKeys) {
  let base = label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  base = base || "field";
  let key = base;
  let n = 2;
  while (usedKeys.has(key)) {
    key = `${base}_${n}`;
    n += 1;
  }
  usedKeys.add(key);
  return key;
}

export default function TemplateFieldsPanel({ template, onClose, onSaved }) {
  const { token } = useAuth();
  const [fields, setFields] = useState([]);
  const [status, setStatus] = useState("none"); // none | discovered | confirmed
  const [isLoading, setLoading] = useState(true);
  const [isDiscovering, setDiscovering] = useState(false);
  const [error, setError] = useState(null);

  // idle | saving | success — drives the whole save state transition
  const [saveState, setSaveState] = useState("idle");
  const [savedCount, setSavedCount] = useState(0);
  const closeTimeoutRef = useRef(null);

  useEffect(() => {
    setLoading(true);
    adminApi
      .getTemplateFields(token, template.id)
      .then((data) => {
        setFields(data.fields);
        setStatus(data.fields_status);
        setError(null);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [template.id, token]);

  // Don't let a pending auto-close fire after the panel's already gone.
  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) clearTimeout(closeTimeoutRef.current);
    };
  }, []);

  const handleDiscover = async () => {
    setDiscovering(true);
    setError(null);
    try {
      const data = await adminApi.discoverTemplateFields(token, template.id);
      setFields(data.fields);
      setStatus(data.fields_status);
    } catch (err) {
      setError(err.message);
    } finally {
      setDiscovering(false);
    }
  };

  const updateField = (index, patch) => {
    setFields((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  };

  const removeField = (index) => {
    setFields((prev) => prev.filter((_, i) => i !== index));
  };

  const addField = () => {
    setFields((prev) => [...prev, { label: "", type: "text", required: false, key: "" }]);
  };

  const handleSave = async () => {
    setError(null);
    const cleanLabels = fields.map((f) => f.label.trim());
    if (fields.length === 0 || cleanLabels.some((l) => !l)) {
      setError("Every field needs a label — remove any blank ones.");
      return;
    }

    const usedKeys = new Set();
    const withKeys = fields.map((f) => ({
      key: slugify(f.label, usedKeys),
      label: f.label.trim(),
      type: f.type,
      required: Boolean(f.required),
    }));

    setSaveState("saving");
    try {
      const data = await adminApi.saveTemplateFields(token, template.id, withKeys);
      setFields(data.fields);
      setStatus(data.fields_status);
      setSavedCount(data.fields.length);
      setSaveState("success");
      // Update the table behind this panel right away, so it's already
      // showing "Confirmed" by the time the panel closes and the admin
      // sees it — no refresh needed to believe the save worked.
      onSaved?.();
      closeTimeoutRef.current = setTimeout(() => {
        onClose();
      }, AUTO_CLOSE_DELAY_MS);
    } catch (err) {
      // Save failed — stay open, keep the edited fields exactly as the
      // admin left them, and surface a clear reason so they can retry.
      setError(err.message);
      setSaveState("idle");
    }
  };

  if (saveState === "success") {
    return (
      <div className="sg-card-section sg-fields-panel">
        <div className="sg-result" style={{ padding: "var(--sg-space-4) 0" }}>
          <div className="sg-result-icon">
            <CheckIcon width={24} height={24} />
          </div>
          <h2 className="sg-result-title">Fields confirmed successfully</h2>
          <p className="sg-result-subtitle" style={{ marginBottom: 0 }}>
            {savedCount} {savedCount === 1 ? "field is" : "fields are"} now configured for
            this template.
          </p>
        </div>
      </div>
    );
  }

  const isSaving = saveState === "saving";

  return (
    <div className="sg-card-section sg-fields-panel">
      <div className="sg-fields-panel-header">
        <div>
          <p className="sg-label" style={{ marginBottom: "4px" }}>
            Fields — {template.name}
          </p>
          <Badge tone={status === "confirmed" ? "success" : status === "discovered" ? "warning" : "neutral"}>
            {status === "confirmed" ? "Confirmed" : status === "discovered" ? "Draft — not yet confirmed" : "No fields yet"}
          </Badge>
        </div>
        <button
          type="button"
          className="sg-file-chip-remove"
          onClick={onClose}
          aria-label="Close"
          disabled={isSaving}
        >
          <CloseIcon width={18} height={18} />
        </button>
      </div>

      {isLoading && <p className="sg-helper">Loading…</p>}

      {!isLoading && (
        <>
          <p className="sg-helper" style={{ marginBottom: "16px" }}>
            {fields.length === 0
              ? "Ask AI to read this template and propose its fields, or add them manually below."
              : "Review the fields below, then confirm — this is what the document workflow will ask users to fill in for this template."}
          </p>

          <Button variant="secondary" onClick={handleDiscover} disabled={isDiscovering || isSaving}>
            {isDiscovering ? "Reading template…" : fields.length === 0 ? "Discover fields with AI" : "Re-discover with AI"}
          </Button>
          {fields.length > 0 && (
            <p className="sg-helper">Re-discovering replaces the list below.</p>
          )}

          {fields.length > 0 && (
            <div className="sg-fields-list">
              {fields.map((field, i) => (
                <div className="sg-fields-row" key={i}>
                  <input
                    className="sg-input"
                    value={field.label}
                    onChange={(e) => updateField(i, { label: e.target.value })}
                    placeholder="Field label, e.g. Vendor name"
                    disabled={isSaving}
                  />
                  <select
                    className="sg-select"
                    value={field.type}
                    onChange={(e) => updateField(i, { type: e.target.value })}
                    disabled={isSaving}
                  >
                    {FIELD_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <label className="sg-fields-required">
                    <input
                      type="checkbox"
                      checked={Boolean(field.required)}
                      onChange={(e) => updateField(i, { required: e.target.checked })}
                      disabled={isSaving}
                    />
                    Required
                  </label>
                  <button
                    type="button"
                    className="sg-file-chip-remove"
                    onClick={() => removeField(i)}
                    aria-label="Remove field"
                    disabled={isSaving}
                  >
                    <CloseIcon width={16} height={16} />
                  </button>
                </div>
              ))}
            </div>
          )}

          <button
            type="button"
            className="sg-btn sg-btn-ghost"
            onClick={addField}
            style={{ marginTop: "8px" }}
            disabled={isSaving}
          >
            + Add field manually
          </button>

          {error && <p className="sg-helper is-warning">{error}</p>}

          {fields.length > 0 && (
            <div className="sg-btn-row">
              <Button variant="primary" onClick={handleSave} disabled={isSaving}>
                {isSaving ? "Saving…" : "Save & confirm fields"}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
