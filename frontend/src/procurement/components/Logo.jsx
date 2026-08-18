import logo from "../assets/solgulf-logo.png";

export default function Logo({ className = "" }) {
  return (
    <img
      src={logo}
      alt="SOLGulf"
      className={`sg-logo-img ${className}`}
    />
  );
}
