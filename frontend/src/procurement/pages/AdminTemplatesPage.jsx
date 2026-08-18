import { useEffect, useRef, useState } from "react";
import Button from "../components/Button";
import Badge from "../components/Badge";
import ConfirmDialog from "../components/ConfirmDialog";
import { UploadIcon } from "../components/icons";
import { useAuth } from "../context/AuthContext";
import * as adminApi from "../api/adminApi";
import TemplateFieldsPanel from "./TemplateFieldsPanel";
import { fileToBase64 } from "../lib/fileToBase64";

export default function AdminTemplatesPage() {
  const { token } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [isLoading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [togglingId, setTogglingId] = useState(null);
  const [fieldsTemplate, setFieldsTemplate] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setDeleting] = useState(false);

  const [name, setName] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const fileInputRef = useRef(null);
  const [formError, setFormError] = useState(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const loadTemplates = () => {
    setLoading(true);
    adminApi
      .listAllTemplates(token)
      .then((data) => {
        setTemplates(data.templates);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadTemplates, [token]);

  const handleToggle = async (template) => {
    const nextStatus = template.status === "active" ? "inactive" : "active";
    setTogglingId(template.id);
    try {
      await adminApi.setTemplateStatus(token, template.id, nextStatus);
      loadTemplates();
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await adminApi.deleteTemplate(token, deleteTarget.id);
      if (fieldsTemplate?.id === deleteTarget.id) setFieldsTemplate(null);
      setDeleteTarget(null);
      loadTemplates();
    } catch (err) {
      setLoadError(err.message);
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!file) {
      setFormError("Choose a .docx file to upload.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".docx")) {
      setFormError("Only .docx files are supported.");
      return;
    }

    setSubmitting(true);
    try {
      const fileBase64 = await fileToBase64(file);
      await adminApi.uploadTemplate(token, {
        name,
        documentType,
        description,
        filename: file.name,
        fileBase64,
      });
      setName("");
      setDocumentType("");
      setDescription("");
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      loadTemplates();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="sg-main">
      <p className="sg-eyebrow">Admin</p>
      <h1 className="sg-title">Manage Templates</h1>

      <div className="sg-admin-page">
        <section className="sg-card">
          <p className="sg-subtitle" style={{ marginTop: 0 }}>
            Only active templates appear in the document workflow's template picker.
          </p>

          {isLoading && <p className="sg-helper">Loading…</p>}
          {loadError && <p className="sg-helper is-warning">{loadError}</p>}

          {!isLoading && !loadError && (
            <div className="sg-table-wrap sg-card-section" style={{ marginTop: 0, paddingTop: 0, borderTop: "none" }}>
              <div className="sg-grid-table sg-grid-table--templates">
                <div className="sg-grid-row">
                  <div className="sg-grid-head">Name</div>
                  <div className="sg-grid-head">Type</div>
                  <div className="sg-grid-head">Status</div>
                  <div className="sg-grid-head">Fields</div>
                  <div className="sg-grid-head">Updated</div>
                  <div className="sg-grid-head"></div>
                </div>

                {templates.map((t) => (
                  <div className="sg-grid-row" key={t.id}>
                    <div className="sg-grid-cell">
                      <div className="sg-grid-cell-stack">
                        <span>{t.name}</span>
                        <span className="sg-table-you">{t.original_filename}</span>
                      </div>
                    </div>
                    <div className="sg-grid-cell is-mono">{t.document_type}</div>
                    <div className="sg-grid-cell">
                      <Badge tone={t.status === "active" ? "success" : "neutral"}>
                        {t.status === "active" ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                    <div className="sg-grid-cell">
                      <Badge
                        tone={
                          t.fields_status === "confirmed"
                            ? "success"
                            : t.fields_status === "discovered"
                            ? "warning"
                            : "neutral"
                        }
                      >
                        {t.fields_status === "confirmed"
                          ? "Confirmed"
                          : t.fields_status === "discovered"
                          ? "Draft"
                          : "Not set"}
                      </Badge>
                    </div>
                    <div className="sg-grid-cell is-mono">{t.updated_at.slice(0, 10)}</div>
                    <div className="sg-grid-cell">
                      <div className="sg-table-actions">
                        <button
                          type="button"
                          className="sg-btn sg-btn-ghost"
                          onClick={() => setFieldsTemplate(t)}
                        >
                          Fields
                        </button>
                        <button
                          type="button"
                          className="sg-btn sg-btn-ghost"
                          onClick={() => handleToggle(t)}
                          disabled={togglingId === t.id}
                        >
                          {togglingId === t.id
                            ? "Please wait…"
                            : t.status === "active"
                            ? "Deactivate"
                            : "Activate"}
                        </button>
                        <button
                          type="button"
                          className="sg-btn sg-btn-ghost sg-btn-danger-text"
                          onClick={() => setDeleteTarget(t)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {fieldsTemplate && (
            <TemplateFieldsPanel
              template={fieldsTemplate}
              onClose={() => setFieldsTemplate(null)}
              onSaved={loadTemplates}
            />
          )}

          <div className="sg-card-section">
            <p className="sg-label" style={{ marginBottom: "16px" }}>
              Upload a new template
            </p>
            <form onSubmit={handleSubmit}>
              <div className="sg-field-row">
                <div className="sg-field" style={{ marginBottom: 0 }}>
                  <label className="sg-label" htmlFor="tmpl-name">
                    Template name
                  </label>
                  <input
                    id="tmpl-name"
                    className="sg-input"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Purchase Order Terms"
                    required
                  />
                </div>
                <div className="sg-field" style={{ marginBottom: 0 }}>
                  <label className="sg-label" htmlFor="tmpl-type">
                    Document type
                  </label>
                  <input
                    id="tmpl-type"
                    className="sg-input"
                    value={documentType}
                    onChange={(e) => setDocumentType(e.target.value)}
                    placeholder="e.g. PO"
                    required
                  />
                </div>
              </div>

              <div className="sg-field">
                <label className="sg-label" htmlFor="tmpl-description">
                  Description
                </label>
                <input
                  id="tmpl-description"
                  className="sg-input"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Short note on when to use this template"
                />
              </div>

              <div className="sg-field">
                <label className="sg-label">Template file (.docx)</label>
                {file ? (
                  <div className="sg-file-chip">
                    <span className="sg-file-chip-icon">
                      <UploadIcon width={16} height={16} />
                    </span>
                    <span className="sg-file-chip-name">{file.name}</span>
                    <button
                      type="button"
                      className="sg-file-chip-remove"
                      onClick={() => {
                        setFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = "";
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="sg-btn sg-btn-secondary"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <UploadIcon width={16} height={16} />
                    Choose file
                  </button>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".docx"
                  className="sg-file-input"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </div>

              {formError && <p className="sg-helper is-warning">{formError}</p>}

              <Button variant="primary" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Uploading…" : "Upload template"}
              </Button>
            </form>
          </div>
        </section>
      </div>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete this template?"
        description={
          deleteTarget
            ? `This permanently removes "${deleteTarget.name}" and its file. This can't be undone.`
            : ""
        }
        confirmLabel="Delete template"
        tone="danger"
        isBusy={isDeleting}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </main>
  );
}
