export default function Badge({ tone = "neutral", children }) {
  return <span className={`sg-badge sg-badge-${tone}`}>{children}</span>;
}
