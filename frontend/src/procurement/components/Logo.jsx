export default function Logo({ className = "" }) {
  return (
    <span
      className={className}
      style={{ fontWeight: 700, fontSize: "1.1rem", color: "var(--sg-navy-900)" }}
    >
      Procurement Document Generator
    </span>
  );
}
