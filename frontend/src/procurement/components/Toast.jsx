export default function Toast({ message }) {
  if (!message) return null;
  return (
    <div className="sg-toast" role="status">
      {message}
    </div>
  );
}
