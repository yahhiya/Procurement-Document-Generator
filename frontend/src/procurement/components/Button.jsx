export default function Button({
  variant = "primary", // "primary" | "secondary" | "ghost"
  block = false,
  className = "",
  children,
  ...rest
}) {
  const classes = [
    "sg-btn",
    `sg-btn-${variant}`,
    block ? "sg-btn-block" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} {...rest}>
      {children}
    </button>
  );
}
