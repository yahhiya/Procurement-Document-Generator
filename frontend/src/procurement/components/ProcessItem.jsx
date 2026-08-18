import { CheckIcon, SpinnerIcon, ClockIcon } from "./icons";

// status: "done" | "active" | "pending"
export default function ProcessItem({ label, status }) {
  return (
    <div className={`sg-process-item is-${status}`}>
      <span className={`sg-process-icon is-${status}`}>
        {status === "done" && <CheckIcon width={14} height={14} />}
        {status === "active" && <SpinnerIcon width={14} height={14} />}
        {status === "pending" && <ClockIcon width={14} height={14} />}
      </span>
      <span className="sg-process-label">{label}</span>
    </div>
  );
}
