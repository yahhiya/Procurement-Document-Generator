import { useEffect, useRef, useState } from "react";
import "./procurement.css";

import Logo from "./components/Logo";
import Stepper from "./components/Stepper";
import SummaryPanel from "./components/SummaryPanel";
import UploadStep from "./pages/UploadStep";
import ReviewStep from "./pages/ReviewStep";
import GenerateStep from "./pages/GenerateStep";
import LoginPage from "./pages/LoginPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import AdminTemplatesPage from "./pages/AdminTemplatesPage";
import { AuthProvider, useAuth } from "./context/AuthContext";
import * as templatesApi from "./api/templatesApi";
import * as documentsApi from "./api/documentsApi";
import { fileToBase64 } from "./lib/fileToBase64";
import { ANALYSIS_STEPS } from "./data/mockData";

function ProcurementWizard() {
  const { token } = useAuth();
  const [step, setStep] = useState("upload"); // upload | review | generate

  const [templates, setTemplates] = useState([]);
  const [templatesStatus, setTemplatesStatus] = useState("loading"); // loading | ready | error
  const [templatesError, setTemplatesError] = useState(null);
  const [selectedTemplateId, setSelectedTemplateId] = useState(null);

  const [file, setFile] = useState(null);
  const [isAnalysing, setIsAnalysing] = useState(false);
  const [completedSteps, setCompletedSteps] = useState(0);
  const [extractError, setExtractError] = useState(null);

  // The real extracted fields for the selected template, and the editable
  // values shown in the review form (seeded from extraction, then edited
  // by the user for anything flagged "not found").
  const [fields, setFields] = useState([]);
  const [values, setValues] = useState({});

  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState(null);
  const [generatedFile, setGeneratedFile] = useState(null); // { blob, name, size }

  // Guards against a slow extraction request finishing after the user has
  // already gone back or cleared the file — its result gets silently
  // dropped instead of clobbering state for a screen no longer showing it.
  const extractionTokenRef = useRef(0);
  const cosmeticTimerRef = useRef(null);

  // Fetch the real, active-only template list from the backend.
  useEffect(() => {
    let cancelled = false;
    setTemplatesStatus("loading");
    templatesApi
      .listTemplates(token)
      .then((data) => {
        if (cancelled) return;
        setTemplates(data.templates);
        setSelectedTemplateId((current) => current ?? data.templates[0]?.id ?? null);
        setTemplatesStatus("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setTemplatesError(err.message);
        setTemplatesStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    return () => {
      if (cosmeticTimerRef.current) clearInterval(cosmeticTimerRef.current);
    };
  }, []);

  const handleGenerate = async () => {
    setStep("generate");
    setIsGenerating(true);
    setGenerateError(null);
    setGeneratedFile(null);
    try {
      const { blob, filename } = await documentsApi.generateDocument(token, {
        templateId: selectedTemplateId,
        values,
      });
      setGeneratedFile({ blob, name: filename, size: blob.size });
      setIsGenerating(false);
    } catch (err) {
      setGenerateError(err.message);
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!generatedFile) return;
    const url = URL.createObjectURL(generatedFile.blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = generatedFile.name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const handleFileSelect = async (selectedFile) => {
    const myToken = ++extractionTokenRef.current;
    setFile(selectedFile);
    setExtractError(null);
    setFields([]);
    setValues({});

    if (!selectedTemplateId) {
      setExtractError("Select a template before uploading a document.");
      return;
    }

    setIsAnalysing(true);
    setCompletedSteps(0);

    // Cosmetic checklist progress while the real request is in flight — it
    // advances up to (but not including) the last step and holds there;
    // the real response is what actually marks the flow complete.
    let i = 0;
    cosmeticTimerRef.current = setInterval(() => {
      i = Math.min(i + 1, ANALYSIS_STEPS.length - 1);
      if (extractionTokenRef.current === myToken) setCompletedSteps(i);
    }, 700);

    try {
      const base64 = await fileToBase64(selectedFile);
      const data = await documentsApi.extractDocument(token, {
        templateId: selectedTemplateId,
        filename: selectedFile.name,
        fileBase64: base64,
      });

      if (extractionTokenRef.current !== myToken) return; // stale — ignore
      clearInterval(cosmeticTimerRef.current);
      setFields(data.fields);
      setValues(Object.fromEntries(data.fields.map((f) => [f.key, f.value ?? ""])));
      setCompletedSteps(ANALYSIS_STEPS.length);
      setIsAnalysing(false);
    } catch (err) {
      if (extractionTokenRef.current !== myToken) return; // stale — ignore
      clearInterval(cosmeticTimerRef.current);
      setIsAnalysing(false);
      setExtractError(err.message);
    }
  };

  const clearFile = () => {
    extractionTokenRef.current += 1; // invalidate any in-flight extraction
    if (cosmeticTimerRef.current) clearInterval(cosmeticTimerRef.current);
    setFile(null);
    setIsAnalysing(false);
    setCompletedSteps(0);
    setExtractError(null);
    setFields([]);
    setValues({});
  };

  const resetAll = () => {
    extractionTokenRef.current += 1;
    if (cosmeticTimerRef.current) clearInterval(cosmeticTimerRef.current);
    setStep("upload");
    setSelectedTemplateId(templates[0]?.id ?? null);
    setFile(null);
    setIsAnalysing(false);
    setCompletedSteps(0);
    setExtractError(null);
    setFields([]);
    setValues({});
    setIsGenerating(false);
    setGenerateError(null);
    setGeneratedFile(null);
  };

  const selectedTemplate = templates.find((t) => t.id === selectedTemplateId) || null;

  const statusByStep = {
    upload: file
      ? extractError
        ? "Couldn't read document"
        : isAnalysing
        ? "Analysing document…"
        : "Analysis complete"
      : "Awaiting upload",
    review: "Reviewing extracted fields",
    generate: generateError ? "Couldn't generate document" : isGenerating ? "Generating document…" : "Document ready",
  };

  return (
    <main className="sg-main">
      <p className="sg-eyebrow">Step {["upload", "review", "generate"].indexOf(step) + 1} of 3</p>
      <h1 className="sg-title">
        {step === "upload" && (file ? "Analysing Requirements Document" : "Upload Requirements & Select Template")}
        {step === "review" && "Review Extracted Fields"}
        {step === "generate" && (isGenerating ? "Generating Document" : generateError ? "Generation Failed" : "Document Ready")}
      </h1>

      <div className="sg-layout">
        <div>
          <Stepper current={step} />

          {step === "upload" && (
            <UploadStep
              templates={templates}
              templatesStatus={templatesStatus}
              templatesError={templatesError}
              selectedTemplateId={selectedTemplateId}
              onTemplateChange={setSelectedTemplateId}
              file={file}
              onFileSelect={handleFileSelect}
              onFileClear={clearFile}
              isAnalysing={isAnalysing}
              completedSteps={completedSteps}
              extractError={extractError}
              onContinue={() => setStep("review")}
            />
          )}

          {step === "review" && (
            <ReviewStep
              fields={fields}
              values={values}
              onChange={(key, value) => setValues((v) => ({ ...v, [key]: value }))}
              onBack={() => setStep("upload")}
              onGenerate={handleGenerate}
            />
          )}

          {step === "generate" && (
            <GenerateStep
              isGenerating={isGenerating}
              generateError={generateError}
              generatedFile={generatedFile}
              onBackToReview={() => setStep("review")}
              onStartNew={resetAll}
              onDownload={handleDownload}
            />
          )}
        </div>

        <SummaryPanel
          template={selectedTemplate?.name}
          file={file?.name}
          status={statusByStep[step]}
        />
      </div>
    </main>
  );
}

function UserChip() {
  const { user, logout } = useAuth();
  return (
    <div className="sg-user-chip">
      <span className="sg-user-email">{user.email}</span>
      <span className={`sg-badge ${user.role === "admin" ? "sg-badge-success" : "sg-badge-neutral"}`}>
        {user.role === "admin" ? "Admin" : "User"}
      </span>
      <button type="button" className="sg-btn sg-btn-ghost" onClick={logout}>
        Sign out
      </button>
    </div>
  );
}

function AppShell() {
  const { status, user } = useAuth();
  const [view, setView] = useState("documents"); // "documents" | "admin-users" | "admin-templates"

  // The nav tabs are admin-only for two of the three views. If someone
  // signs out of an admin account while on "Manage Templates" and a
  // different, non-admin user signs in in the same tab, `view` would still
  // point at an admin-only screen that user can't see — and nothing would
  // render. Reset to "documents" on every new login so that can't happen.
  useEffect(() => {
    if (user) setView("documents");
  }, [user?.id]);

  // Extra safety net: if `view` is ever something this user isn't allowed
  // to see (belt-and-braces alongside the effect above), fall back to
  // "documents" rather than rendering nothing.
  const isAdminView = view === "admin-users" || view === "admin-templates";
  const effectiveView = isAdminView && user?.role !== "admin" ? "documents" : view;

  return (
    <div className="sg-app">
      <header className="sg-header">
        <Logo />
        {status === "authenticated" && (
          <nav className="sg-nav-tabs" aria-label="Sections">
            <button
              type="button"
              className={`sg-nav-tab ${effectiveView === "documents" ? "is-active" : ""}`}
              onClick={() => setView("documents")}
            >
              Documents
            </button>
            {user.role === "admin" && (
              <button
                type="button"
                className={`sg-nav-tab ${effectiveView === "admin-templates" ? "is-active" : ""}`}
                onClick={() => setView("admin-templates")}
              >
                Manage Templates
              </button>
            )}
            {user.role === "admin" && (
              <button
                type="button"
                className={`sg-nav-tab ${effectiveView === "admin-users" ? "is-active" : ""}`}
                onClick={() => setView("admin-users")}
              >
                Manage Users
              </button>
            )}
          </nav>
        )}
        {status === "authenticated" ? (
          <UserChip />
        ) : (
          <span className="sg-header-meta">Procurement Document Generator</span>
        )}
      </header>

      {status === "loading" && (
        <main className="sg-main">
          <p className="sg-subtitle">Loading…</p>
        </main>
      )}
      {status === "anonymous" && <LoginPage />}
      {status === "authenticated" && effectiveView === "documents" && <ProcurementWizard />}
      {status === "authenticated" && effectiveView === "admin-users" && <AdminUsersPage />}
      {status === "authenticated" && effectiveView === "admin-templates" && <AdminTemplatesPage />}

      <footer className="sg-footer">Built by Yahhiya Khawaja for SOLGulf</footer>
    </div>
  );
}

export default function ProcurementApp() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}
