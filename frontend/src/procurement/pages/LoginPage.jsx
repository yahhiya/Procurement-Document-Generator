import { useEffect, useState } from "react";
import Button from "../components/Button";
import { useAuth } from "../context/AuthContext";
import * as authApi from "../api/authApi";

export default function LoginPage() {
  const { login, register } = useAuth();
  // null while we check the backend, then true (no admin yet) or false.
  const [needsSetup, setNeedsSetup] = useState(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setSubmitting] = useState(false);

  useEffect(() => {
    authApi
      .setupStatus()
      .then((data) => setNeedsSetup(data.needs_setup))
      .catch(() => setNeedsSetup(false)); // assume normal sign-in if the check fails
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (needsSetup) {
        await register(email, password);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (needsSetup === null) {
    return (
      <div className="sg-login">
        <p className="sg-subtitle">Checking workspace…</p>
      </div>
    );
  }

  return (
    <div className="sg-login">
      <div className="sg-login-card">
        <h1 className="sg-login-title">
          {needsSetup ? "Set up your workspace" : "Sign in"}
        </h1>
        <p className="sg-subtitle" style={{ marginTop: 0 }}>
          {needsSetup
            ? "Create the first account — it becomes the workspace admin."
            : "Sign in to generate procurement documents."}
        </p>

        <form onSubmit={handleSubmit}>
          <div className="sg-field">
            <label className="sg-label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className="sg-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="sg-field">
            <label className="sg-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="sg-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={needsSetup ? "new-password" : "current-password"}
              minLength={8}
              required
            />
            {needsSetup && <p className="sg-helper">At least 8 characters.</p>}
          </div>

          {error && <p className="sg-helper is-warning">{error}</p>}

          <Button variant="primary" block type="submit" disabled={isSubmitting}>
            {isSubmitting
              ? "Please wait…"
              : needsSetup
              ? "Create admin account"
              : "Sign in"}
          </Button>
        </form>

        {!needsSetup && (
          <p className="sg-helper" style={{ textAlign: "center", marginTop: "20px" }}>
            Don't have an account? Ask your workspace admin to create one for you.
          </p>
        )}
      </div>
    </div>
  );
}
