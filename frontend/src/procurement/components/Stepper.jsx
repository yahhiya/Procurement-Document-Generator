import { CheckIcon } from "./icons";

const STEPS = [
  { key: "upload", label: "Upload" },
  { key: "review", label: "Review" },
  { key: "generate", label: "Generate" },
];

export default function Stepper({ current }) {
  const currentIndex = STEPS.findIndex((s) => s.key === current);

  return (
    <div className="sg-stepper" role="list" aria-label="Document generation progress">
      {STEPS.map((step, i) => {
        const isDone = i < currentIndex;
        const isActive = i === currentIndex;
        const circleClass = isDone ? "is-done" : isActive ? "is-active" : "";
        const labelClass = isDone ? "is-done" : isActive ? "is-active" : "";

        return (
          <div className="sg-step" key={step.key} role="listitem">
            <div className="sg-step-node">
              <div className={`sg-step-circle ${circleClass}`}>
                {isDone ? <CheckIcon width={14} height={14} /> : i + 1}
              </div>
              <span className={`sg-step-label ${labelClass}`}>{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`sg-step-connector ${isDone ? "is-done" : ""}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
