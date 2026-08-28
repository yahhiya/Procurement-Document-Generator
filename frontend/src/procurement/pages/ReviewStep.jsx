import Button from "../components/Button";
import Badge from "../components/Badge";
import { ArrowRightIcon } from "../components/icons";

const MONO_TYPES = new Set(["currency", "number"]);

function Field({ field, value, onChange }) {
  // A field is flagged if extraction couldn't find it AND the user hasn't
  // since filled it in themselves.
  const isEmpty = field.needsVerification && !value;

  return (
    <div className="sg-field">
      <div className="sg-label-row">
        <label className="sg-label" htmlFor={field.key}>
          {field.label}
        </label>
        {isEmpty && <Badge tone="warning">Needs verification</Badge>}
      </div>
      <input
        id={field.key}
        className={`sg-input ${MONO_TYPES.has(field.type) ? "is-mono" : ""} ${isEmpty ? "has-warning" : ""}`}
        value={value}
        placeholder={isEmpty ? "Not found" : undefined}
        onChange={(e) => onChange(field.key, e.target.value)}
      />
      {isEmpty && (
        <p className="sg-helper is-warning">
          Not found automatically — please confirm before generating.
        </p>
      )}
    </div>
  );
}

export default function ReviewStep({ fields, values, onChange, onBack, onGenerate, isDemo = false }) {
  const hasUnresolvedField = fields.some((f) => f.needsVerification && !values[f.key]);

  return (
    <section className="sg-card">
      {isDemo && (
        <div className="sg-demo-banner">
          <span className="sg-demo-banner-icon">✨</span>
          <p className="sg-demo-banner-text">
            <strong>AI has extracted these fields for you</strong> from the requirements document.
            This is the review step — in normal use, you'd check each value is correct (or edit
            anything that isn't) before generating the final contract.
          </p>
        </div>
      )}
      <p className="sg-subtitle" style={{ marginTop: 0 }}>
        Confirm the fields before generating.
      </p>

      {fields.map((field) => (
        <Field field={field} value={values[field.key]} onChange={onChange} key={field.key} />
      ))}

      <div className="sg-btn-row">
        <Button variant="secondary" onClick={onBack}>
          ← Back
        </Button>
        <Button variant="primary" onClick={onGenerate} disabled={hasUnresolvedField}>
          Generate document <ArrowRightIcon width={16} height={16} />
        </Button>
      </div>
      {hasUnresolvedField && (
        <p className="sg-helper is-warning" style={{ textAlign: "center" }}>
          Resolve the flagged field to continue.
        </p>
      )}
    </section>
  );
}
