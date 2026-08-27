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
import { ANALYSIS_STEPS, DEMO_ANALYSIS_STEPS } from "./data/mockData";

// Cosmetic-only: how long the demo's loading state stays up before showing
// the pre-filled review screen. Real extraction has no fixed floor — it
// finishes whenever the real request resolves — but the demo has no
// request to wait on, so this is what gives it the "working" feel the
// button promises instead of an instant, jarring snap to the next screen.
const DEMO_LOADING_MS = 2000;

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

  // Demo mode: true from the moment "Try Interactive Demo" is clicked until
  // the wizard is reset. Swaps in demo-flavoured loading copy in place of
  // real upload + extraction wording. Everything downstream (review, edit,
  // generate, download) runs through the exact same code path as a real
  // document.
  const [isDemo, setIsDemo] = useState(false);

  // Populated by "Try Interactive Demo": template info + pre-staged field
  // values, fetched immediately but held here rather than applied straight
  // away. Nothing about the flow "runs" yet — the user sees the sample
  // template and file attached first, same as they'd see their own
  // choices before a real upload kicks off, and only starts analysis
  // when they click through (see handleAnalyzeDemo below).
  const [demoData, setDemoData] = useState(null);

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
        setSelectedTemplateId(
          (current) => current ?? data.templates[0]?.id ?? null
        );
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
      if (cosmeticTimerRef.current) {
        clearInterval(cosmeticTimerRef.current);
      }
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

      setGeneratedFile({
        blob,
        name: filename,
        size: blob.size,
      });

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

    // Cosmetic checklist progress while the real request is in flight.
    // It advances up to (but does not include) the last step and holds there;
    // the real response is what actually marks the flow complete.
    let i = 0;

    cosmeticTimerRef.current = setInterval(() => {
      i = Math.min(i + 1, ANALYSIS_STEPS.length - 1);

      if (extractionTokenRef.current === myToken) {
        setCompletedSteps(i);
      }
    }, 700);

    try {
      const base64 = await fileToBase64(selectedFile);

      const data = await documentsApi.extractDocument(token, {
        templateId: selectedTemplateId,
        filename: selectedFile.name,
        fileBase64: base64,
      });

      if (extractionTokenRef.current !== myToken) return;

      clearInterval(cosmeticTimerRef.current);

      setFields(data.fields);

      setValues(
        Object.fromEntries(
          data.fields.map((f) => [f.key, f.value ?? ""])
        )
      );

      setCompletedSteps(ANALYSIS_STEPS.length);
      setIsAnalysing(false);
    } catch (err) {
      if (extractionTokenRef.current !== myToken) return;

      clearInterval(cosmeticTimerRef.current);

      setIsAnalysing(false);
      setExtractError(err.message);
    }
  };

  // Phase 1: clicking "⚡ Try Interactive Demo". Fetches the sample data
  // (near-instant — no LLM call, pure lookup) and shows the sample
  // template + a sample file attached, exactly like a real user would see
  // right after picking a template and dropping a file — but doesn't
  // start "analysing" yet. That happens in handleAnalyzeDemo, once the
  // user actually clicks through, so the demo has the same two-step feel
  // (attach, then analyze) as the real flow instead of jumping straight
  // to a progress screen.
  const handleTryDemo = async () => {
    const myToken = ++extractionTokenRef.current;

    setIsDemo(true);
    setExtractError(null);
    setFields([]);
    setValues({});
    setIsAnalysing(false);
    setCompletedSteps(0);

    try {
      const data = await documentsApi.getDemoSample(token);
      if (extractionTokenRef.current !== myToken) return;

      setDemoData(data);
      setSelectedTemplateId(data.template.id);
      // A lightweight stand-in for a real File — only ever read for
      // .name/.size (Dropzone/SummaryPanel display), never sent anywhere
      // or passed to fileToBase64, so it doesn't need to be a real File.
      setFile({ name: "Sample_Requirements.docx", size: 48200 });
    } catch (err) {
      if (extractionTokenRef.current !== myToken) return;
      setExtractError(err.message);
    }
  };

  // Phase 2: clicking "Analyze Document" on the ready screen. Runs the
  // same cosmetic checklist mechanic as a real upload, timed to
  // DEMO_LOADING_MS, then applies the already-fetched demo fields/values —
  // no second network call needed.
  const handleAnalyzeDemo = () => {
    const myToken = ++extractionTokenRef.current;
    if (!demoData) return;

    setIsAnalysing(true);
    setCompletedSteps(0);

    let i = 0;
    const stepInterval = DEMO_LOADING_MS / DEMO_ANALYSIS_STEPS.length;
    cosmeticTimerRef.current = setInterval(() => {
      i = Math.min(i + 1, DEMO_ANALYSIS_STEPS.length - 1);
      if (extractionTokenRef.current === myToken) {
        setCompletedSteps(i);
      }
    }, stepInterval);

    setTimeout(() => {
      if (extractionTokenRef.current !== myToken) return;

      clearInterval(cosmeticTimerRef.current);

      setFields(demoData.fields);
      setValues(Object.fromEntries(demoData.fields.map((f) => [f.key, f.value ?? ""])));

      setCompletedSteps(DEMO_ANALYSIS_STEPS.length);
      setIsAnalysing(false);
    }, DEMO_LOADING_MS);
  };

  const clearFile = () => {
    extractionTokenRef.current += 1;

    if (cosmeticTimerRef.current) {
      clearInterval(cosmeticTimerRef.current);
    }

    setFile(null);
    setIsDemo(false);
    setDemoData(null);
    setIsAnalysing(false);
    setCompletedSteps(0);
    setExtractError(null);
    setFields([]);
    setValues({});
  };

  const resetAll = () => {
    extractionTokenRef.current += 1;

    if (cosmeticTimerRef.current) {
      clearInterval(cosmeticTimerRef.current);
    }

    setStep("upload");
    setSelectedTemplateId(templates[0]?.id ?? null);
    setFile(null);
    setIsDemo(false);
    setDemoData(null);
    setIsAnalysing(false);
    setCompletedSteps(0);
    setExtractError(null);
    setFields([]);
    setValues({});
    setIsGenerating(false);
    setGenerateError(null);
    setGeneratedFile(null);
  };

  // The demo template is deliberately excluded from the real `templates`
  // list (see backend/demo_seed.py), so it won't be found by the lookup
  // below while a demo is in progress — fall back to the name that came
  // back with the demo data itself.
  const selectedTemplate =
    (isDemo && demoData?.template) ||
    templates.find((t) => t.id === selectedTemplateId) ||
    null;

  const isDemoReady = isDemo && Boolean(file) && !isAnalysing && completedSteps === 0;

  const statusByStep = {
    upload: file
      ? extractError
        ? "Couldn't read document"
        : isDemoReady
        ? "Sample ready — click Analyze"
        : isAnalysing
        ? "Analysing document…"
        : "Analysis complete"
      : "Awaiting upload",

    review: "Reviewing extracted fields",

    generate: generateError
      ? "Couldn't generate document"
      : isGenerating
      ? "Generating document…"
      : "Document ready",
  };

  return (
    <main className="sg-main">
      <p className="sg-eyebrow">
        Step {["upload", "review", "generate"].indexOf(step) + 1} of 3
      </p>

      <h1 className="sg-title">
        {step === "upload" &&
          (file
            ? isDemoReady
              ? "Sample Contract Ready"
              : "Analysing Requirements Document"
            : "Upload Requirements & Select Template")}

        {step === "review" && "Review Extracted Fields"}

        {step === "generate" &&
          (isGenerating
            ? "Generating Document"
            : generateError
            ? "Generation Failed"
            : "Document Ready")}
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
              selectedTemplateName={selectedTemplate?.name}
              file={file}
              onFileSelect={handleFileSelect}
              onFileClear={clearFile}
              isAnalysing={isAnalysing}
              completedSteps={completedSteps}
              steps={isDemo ? DEMO_ANALYSIS_STEPS : ANALYSIS_STEPS}
              extractError={extractError}
              onContinue={() => setStep("review")}
              onTryDemo={handleTryDemo}
              isDemo={isDemo}
              onAnalyzeDemo={handleAnalyzeDemo}
            />
          )}

          {step === "review" && (
            <ReviewStep
              fields={fields}
              values={values}
              onChange={(key, value) =>
                setValues((v) => ({
                  ...v,
                  [key]: value,
                }))
              }
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

      <span
        className={`sg-badge ${
          user.role === "admin"
            ? "sg-badge-success"
            : "sg-badge-neutral"
        }`}
      >
        {user.role === "admin" ? "Admin" : "User"}
      </span>

      <button
        type="button"
        className="sg-btn sg-btn-ghost"
        onClick={logout}
      >
        Sign out
      </button>
    </div>
  );
}

function AppShell() {
  const { status, user } = useAuth();
  const [view, setView] = useState("documents");
  // "documents" | "admin-users" | "admin-templates"

  // Reset to documents on every new login so an admin-only screen
  // cannot remain selected when a different user signs in.
  useEffect(() => {
    if (user) {
      setView("documents");
    }
  }, [user?.id]);

  // Extra safety net: if the selected view is admin-only and the
  // current user isn't an admin, fall back to documents.
  const isAdminView =
    view === "admin-users" || view === "admin-templates";

  const effectiveView =
    isAdminView && user?.role !== "admin"
      ? "documents"
      : view;

  return (
    <div className="sg-app">
      <header className="sg-header">
        <Logo />

        {status === "authenticated" && (
          <nav className="sg-nav-tabs" aria-label="Sections">
            <button
              type="button"
              className={`sg-nav-tab ${
                effectiveView === "documents" ? "is-active" : ""
              }`}
              onClick={() => setView("documents")}
            >
              Documents
            </button>

            {user.role === "admin" && (
              <button
                type="button"
                className={`sg-nav-tab ${
                  effectiveView === "admin-templates"
                    ? "is-active"
                    : ""
                }`}
                onClick={() => setView("admin-templates")}
              >
                Manage Templates
              </button>
            )}

            {user.role === "admin" && (
              <button
                type="button"
                className={`sg-nav-tab ${
                  effectiveView === "admin-users"
                    ? "is-active"
                    : ""
                }`}
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
          <span className="sg-header-meta">
            Procurement Document Generator
          </span>
        )}
      </header>

      {status === "loading" && (
        <main className="sg-main">
          <p className="sg-subtitle">Loading…</p>
        </main>
      )}

      {status === "anonymous" && <LoginPage />}

      {status === "authenticated" &&
        effectiveView === "documents" && <ProcurementWizard />}

      {status === "authenticated" &&
        effectiveView === "admin-users" && <AdminUsersPage />}

      {status === "authenticated" &&
        effectiveView === "admin-templates" && (
          <AdminTemplatesPage />
        )}
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