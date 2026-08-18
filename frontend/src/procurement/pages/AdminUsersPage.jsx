import { useEffect, useState } from "react";
import Button from "../components/Button";
import Badge from "../components/Badge";
import ConfirmDialog from "../components/ConfirmDialog";
import { useAuth } from "../context/AuthContext";
import * as adminApi from "../api/adminApi";

export default function AdminUsersPage() {
  const { token, user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [isLoading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionError, setActionError] = useState(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [formError, setFormError] = useState(null);
  const [isSubmitting, setSubmitting] = useState(false);
  const [confirmAdminRole, setConfirmAdminRole] = useState(false);

  const [removeTarget, setRemoveTarget] = useState(null);
  const [isRemoving, setRemoving] = useState(false);

  const loadUsers = () => {
    setLoading(true);
    adminApi
      .listUsers(token)
      .then((data) => {
        setUsers(data.users);
        setLoadError(null);
      })
      .catch((err) => setLoadError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadUsers, [token]);

  // The earliest-created admin — mirrors the backend's definition exactly,
  // used here only to guide the UI (the backend enforces this regardless).
  const admins = users.filter((u) => u.role === "admin");
  const primaryAdminId = admins.length
    ? admins.reduce((min, u) => (u.id < min ? u.id : min), admins[0].id)
    : null;

  const canRemove = (u) => {
    if (u.id === primaryAdminId) return false;
    if (u.role === "admin") {
      return currentUser.id === primaryAdminId && admins.length > 1;
    }
    return true;
  };

  const removeDisabledReason = (u) => {
    if (u.id === primaryAdminId) return "The primary admin can't be removed.";
    if (u.role === "admin" && admins.length <= 1) return "Can't remove the last admin.";
    if (u.role === "admin" && currentUser.id !== primaryAdminId) {
      return "Only the primary admin can remove another admin.";
    }
    return "";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await adminApi.createUser(token, { email, password, role });
      setEmail("");
      setPassword("");
      setRole("user");
      loadUsers();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleRoleChange = (value) => {
    if (value === "admin") {
      setConfirmAdminRole(true);
    } else {
      setRole(value);
    }
  };

  const handleRemove = async () => {
    if (!removeTarget) return;
    setRemoving(true);
    try {
      await adminApi.deleteUser(token, removeTarget.id);
      setRemoveTarget(null);
      loadUsers();
    } catch (err) {
      setActionError(err.message);
      setRemoveTarget(null);
    } finally {
      setRemoving(false);
    }
  };

  return (
    <main className="sg-main">
      <p className="sg-eyebrow">Admin</p>
      <h1 className="sg-title">Manage Users</h1>

      <div className="sg-admin-page">
        <section className="sg-card">
          <p className="sg-subtitle" style={{ marginTop: 0 }}>
            Everyone with access to this workspace.
          </p>

          {isLoading && <p className="sg-helper">Loading…</p>}
          {loadError && <p className="sg-helper is-warning">{loadError}</p>}
          {actionError && <p className="sg-helper is-warning">{actionError}</p>}

          {!isLoading && !loadError && (
            <div className="sg-table-wrap sg-card-section" style={{ marginTop: 0, paddingTop: 0, borderTop: "none" }}>
              <div className="sg-grid-table sg-grid-table--users">
                <div className="sg-grid-row">
                  <div className="sg-grid-head">Email</div>
                  <div className="sg-grid-head">Role</div>
                  <div className="sg-grid-head">Added</div>
                  <div className="sg-grid-head"></div>
                </div>

                {users.map((u) => (
                  <div className="sg-grid-row" key={u.id}>
                    <div className="sg-grid-cell">
                      <span>{u.email}</span>
                      {u.id === currentUser.id && (
                        <span className="sg-table-you">&nbsp;(you)</span>
                      )}
                      {u.id === primaryAdminId && (
                        <span className="sg-table-you">&nbsp;· primary admin</span>
                      )}
                    </div>
                    <div className="sg-grid-cell">
                      <Badge tone={u.role === "admin" ? "success" : "neutral"}>
                        {u.role === "admin" ? "Admin" : "User"}
                      </Badge>
                    </div>
                    <div className="sg-grid-cell is-mono">{u.created_at.slice(0, 10)}</div>
                    <div className="sg-grid-cell">
                      <button
                        type="button"
                        className="sg-btn sg-btn-ghost sg-btn-danger-text"
                        disabled={!canRemove(u)}
                        title={canRemove(u) ? undefined : removeDisabledReason(u)}
                        onClick={() => setRemoveTarget(u)}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="sg-card-section">
            <p className="sg-label" style={{ marginBottom: "16px" }}>
              Add a teammate
            </p>
            <form onSubmit={handleSubmit}>
              <div className="sg-field-row">
                <div className="sg-field" style={{ marginBottom: 0 }}>
                  <label className="sg-label" htmlFor="new-email">
                    Email
                  </label>
                  <input
                    id="new-email"
                    type="email"
                    className="sg-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
                <div className="sg-field" style={{ marginBottom: 0 }}>
                  <label className="sg-label" htmlFor="new-role">
                    Role
                  </label>
                  <select
                    id="new-role"
                    className="sg-select"
                    value={role}
                    onChange={(e) => handleRoleChange(e.target.value)}
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>

              <div className="sg-field">
                <label className="sg-label" htmlFor="new-password">
                  Temporary password
                </label>
                <input
                  id="new-password"
                  type="text"
                  className="sg-input is-mono"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={8}
                  placeholder="At least 8 characters"
                  required
                />
                <p className="sg-helper">
                  Share this with them directly — there's no email invite yet, so send it
                  some other way (Slack, in person, etc).
                </p>
              </div>

              {formError && <p className="sg-helper is-warning">{formError}</p>}

              <Button variant="primary" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Adding…" : "Add teammate"}
              </Button>
            </form>
          </div>
        </section>
      </div>

      <ConfirmDialog
        open={confirmAdminRole}
        title="Grant admin access?"
        description="You selected Admin. Admins can manage templates and other users' accounts. Are you sure you want to grant full admin access?"
        confirmLabel="Yes, make them admin"
        tone="danger"
        onConfirm={() => {
          setRole("admin");
          setConfirmAdminRole(false);
        }}
        onCancel={() => setConfirmAdminRole(false)}
      />

      <ConfirmDialog
        open={Boolean(removeTarget)}
        title="Remove this account?"
        description={
          removeTarget
            ? `"${removeTarget.email}" will no longer be able to sign in. This can't be undone.`
            : ""
        }
        confirmLabel="Remove access"
        tone="danger"
        isBusy={isRemoving}
        onConfirm={handleRemove}
        onCancel={() => setRemoveTarget(null)}
      />
    </main>
  );
}
