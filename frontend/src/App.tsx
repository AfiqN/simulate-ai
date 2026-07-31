import { useEffect, useState, lazy, Suspense } from "react";
import { Routes, Route, useNavigate, useParams } from "react-router-dom";
import { useSimulation, useSimulationEvents, getPersistedRun } from "./hooks/useSimulation";
import { useWebSocket } from "./hooks/useWebSocket";
import { useNotification } from "./hooks/useNotification";
import { useDocumentTitle } from "./hooks/useDocumentTitle";
import { startSimulation, approveSchema, cancelSimulation, getRunDetail } from "./lib/api";
import { Header } from "./components/layout/Header";
import { SettingsPanel } from "./components/layout/SettingsPanel";
import { LandingHero } from "./components/layout/LandingHero";
import { SimForm } from "./components/simulation/SimForm";
import { SimulationLive } from "./components/simulation/SimulationLive";
import { TemplateGallery } from "./components/templates/TemplateGallery";
import type { SimulationConfig } from "./types";
import type { ExampleData } from "./lib/transformMetrics";

const ResultsView = lazy(() => import("./components/simulation/ResultsView").then(m => ({ default: m.ResultsView })));
const SchemaApproval = lazy(() => import("./components/simulation/SchemaApproval").then(m => ({ default: m.SchemaApproval })));

export default function App() {
  const [showSettings, setShowSettings] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastStimulus, setLastStimulus] = useState("");
  const [lastDepth, setLastDepth] = useState<string>("standard");
  const [startedAt, setStartedAt] = useState<number | undefined>(undefined);
  const [templatePreFill, setTemplatePreFill] = useState<{ stimulus: string; depth: string; agents: number } | null>(null);
  const [refineContext, setRefineContext] = useState<{ originalStimulus: string; previousVerdict: string; scenarioName: string; depth: string; agents: number } | null>(null);

  const { state, dispatch } = useSimulation();
  const { events, status: wsStatus } = useWebSocket(state.runId);
  const { notify } = useNotification();
  const navigate = useNavigate();

  useSimulationEvents(dispatch, events);
  useDocumentTitle(state.status, state.progress);

  // Recover active run on mount
  useEffect(() => {
    const persisted = getPersistedRun();
    if (persisted) {
      getRunDetail(persisted.runId).then((data) => {
        if (data.status === "completed" && data.result) {
          dispatch({ type: "LOAD_RESULT", result: data.result });
          navigate(`/run/${persisted.runId}`, { replace: true });
        } else if (data.status === "running" || data.status === "queued") {
          dispatch({ type: "RECOVER", runId: persisted.runId, progress: data.progress ?? 0, stage: data.stage });
          setLastDepth(persisted.depth || "standard");
          setStartedAt(persisted.startedAt);
          if (persisted.stimulus) setLastStimulus(persisted.stimulus);
          navigate(`/run/${persisted.runId}`, { replace: true });
        }
      }).catch(() => {
        dispatch({ type: "RESET" });
        try { localStorage.removeItem("simulate-ai-active-run"); } catch {}
      });
    }
  }, []);

  // Notify on completion
  useEffect(() => {
    if (state.status === "complete" && state.result) {
      notify("Simulation complete", `Verdict: ${state.result.verdict || "Done"}`);
    } else if (state.status === "error") {
      notify("Simulation failed", state.error || "An error occurred");
    }
  }, [state.status]);

  // Redirect to /run/:id when simulation starts
  useEffect(() => {
    if (state.status === "running" && state.runId) {
      navigate(`/run/${state.runId}`, { replace: true });
    }
  }, [state.status, state.runId]);

  const handleSubmit = async (config: SimulationConfig) => {
    setSubmitError(null);
    setLastStimulus(config.stimulus);
    setLastDepth(config.depth);
    setStartedAt(Date.now());
    try {
      const { id } = await startSimulation(config);
      dispatch({ type: "START", runId: id });
      localStorage.setItem("simulate-ai-active-run", JSON.stringify({
        runId: id,
        startedAt: Date.now(),
        depth: config.depth,
        stimulus: config.stimulus,
      }));
    } catch (err: any) {
      setSubmitError(err.message || "Failed to start simulation");
    }
  };

  const handleApproveSchema = async () => {
    if (!state.runId) return;
    try {
      await approveSchema(state.runId);
      dispatch({ type: "SCHEMA_APPROVED" });
    } catch (err) {
      console.error("Failed to approve schema:", err);
    }
  };

  const handleCancel = async () => {
    if (!state.runId) return;
    try {
      await cancelSimulation(state.runId);
      dispatch({ type: "RESET" });
      navigate("/");
    } catch (err) {
      console.error("Failed to cancel simulation:", err);
    }
  };

  const handleReset = () => {
    dispatch({ type: "RESET" });
    setSubmitError(null);
    setTemplatePreFill(null);
    setRefineContext(null);
    try { localStorage.removeItem("simulate-ai-active-run"); } catch {}
    navigate("/");
  };

  const handleRefine = (originalStimulus: string, previousVerdict: string, scenarioName: string, depth: string, agents: number) => {
    setRefineContext({ originalStimulus, previousVerdict, scenarioName, depth, agents });
    dispatch({ type: "RESET" });
    navigate("/simulate");
  };

  const handleLoadExample = (data: ExampleData) => {
    dispatch({
      type: "LOAD_EXAMPLE",
      result: data.result,
      rounds: data.rounds,
      agentsByRound: data.agentsByRound,
      factionUpdates: data.factionUpdates,
      triggersEvents: data.triggersEvents,
      historicalPrecedents: data.historicalPrecedents,
      adversarialResult: data.adversarialResult,
    });
    navigate("/run/example");
  };

  const handleSelectTemplate = (stimulus: string, depth: "quick" | "standard" | "deep", agents: number) => {
    setTemplatePreFill({ stimulus, depth, agents });
    navigate("/simulate");
  };

  const latestRound = Math.max(...Object.keys(state.agentsByRound).map(Number), 0);
  const latestAgents = state.agentsByRound[latestRound] || [];

  return (
    <div className="min-h-screen">
      <Header onOpenSettings={() => setShowSettings(true)} onLogoClick={handleReset} />
      <SettingsPanel open={showSettings} onClose={() => setShowSettings(false)} />

      <main className="mx-auto max-w-[960px] px-6 py-6 space-y-6">
        <Routes>
          {/* Landing */}
          <Route path="/" element={
            <LandingHero
              onGetStarted={() => navigate("/simulate")}
              onLoadExample={handleLoadExample}
              onShowTemplates={() => navigate("/templates")}
            />
          } />

          {/* Templates */}
          <Route path="/templates" element={
            <TemplateGallery
              onSelect={handleSelectTemplate}
              onBack={() => navigate("/")}
            />
          } />

          {/* Simulate form */}
          <Route path="/simulate" element={
            <>
              <SimForm
                onSubmit={handleSubmit}
                disabled={state.status === "running" || state.status === "schema_pending"}
                prefill={templatePreFill}
                onClearPrefill={() => setTemplatePreFill(null)}
                onBackToTemplates={() => navigate("/templates")}
                refineContext={refineContext}
                onClearRefine={() => setRefineContext(null)}
              />
              {submitError && (
                <div className="border border-[#8B1A1A]/20 rounded-[6px] bg-[#FEF2F2] p-4 flex items-start gap-3">
                  <div className="flex-1">
                    <p className="text-[14px] text-[#8B1A1A]">{submitError}</p>
                    {submitError.includes("Demo limit") && (
                      <button
                        onClick={() => setShowSettings(true)}
                        className="mt-2 text-[13px] text-[#8B1A1A] underline font-medium"
                      >
                        Add your own API key for unlimited access
                      </button>
                    )}
                  </div>
                  <button onClick={() => setSubmitError(null)} className="text-[#8B1A1A]/60 hover:text-[#8B1A1A] text-[18px]">&times;</button>
                </div>
              )}
              {state.status === "schema_pending" && state.schema && (
                <Suspense fallback={<div className="py-10 text-center text-[13px] text-[#8B8B8B]">Loading...</div>}>
                  <SchemaApproval schema={state.schema} onApprove={handleApproveSchema} />
                </Suspense>
              )}
            </>
          } />

          {/* Run (live + results) */}
          <Route path="/run/:id" element={
            <RunView
              state={state}
              latestAgents={latestAgents}
              latestRound={latestRound}
              lastStimulus={lastStimulus}
              lastDepth={lastDepth}
              startedAt={startedAt}
              wsStatus={wsStatus}
              onCancel={handleCancel}
              onReset={handleReset}
              onRefine={handleRefine}
              dispatch={dispatch}
            />
          } />
        </Routes>
      </main>
    </div>
  );
}

// Sub-component to handle /run/:id view
function RunView({ state, latestAgents, latestRound, lastStimulus, lastDepth, startedAt, wsStatus, onCancel, onReset, onRefine, dispatch }: any) {
  const { id } = useParams();
  const navigate = useNavigate();

  // Load shared run by URL if we don't have state for it
  useEffect(() => {
    if (id && id !== "example" && state.status === "idle" && !state.runId) {
      getRunDetail(id).then((data) => {
        if (data.status === "completed" && data.result) {
          dispatch({ type: "LOAD_RESULT", result: data.result });
        } else if (data.status === "running" || data.status === "queued") {
          dispatch({ type: "RECOVER", runId: id, progress: data.progress ?? 0, stage: data.stage });
        }
      }).catch(() => {
        navigate("/", { replace: true });
      });
    }
  }, [id, state.status]);

  if (state.status === "running") {
    return (
      <SimulationLive
        currentStage={state.currentStage}
        progress={state.progress}
        agents={state.agents}
        latestAgents={latestAgents}
        latestRound={latestRound}
        stimulus={lastStimulus}
        depth={lastDepth}
        startedAt={startedAt}
        wsConnected={wsStatus === "connected"}
        onCancel={onCancel}
      />
    );
  }

  if (state.status === "error") {
    return (
      <div className="border border-[#8B1A1A]/20 rounded-[6px] bg-[#FEF2F2] p-4">
        <p className="text-[14px] text-[#8B1A1A]">{state.error}</p>
        <button onClick={onReset} className="mt-3 text-[13px] text-[#8B1A1A] underline">
          Start over
        </button>
      </div>
    );
  }

  if (state.status === "complete" && state.result) {
    return (
      <Suspense fallback={<div className="py-10 text-center text-[13px] text-[#8B8B8B]">Loading results...</div>}>
        <ResultsView
          result={state.result}
          rounds={state.rounds}
          agentsByRound={state.agentsByRound}
          schema={state.schema}
          factionUpdates={state.factionUpdates}
          triggersEvents={state.triggersEvents}
          historicalPrecedents={state.historicalPrecedents}
          adversarialResult={state.adversarialResult}
          runId={state.runId || id}
          onReset={onReset}
          onRefine={onRefine}
        />
      </Suspense>
    );
  }

  // Loading state
  return (
    <div className="py-20 text-center text-[13px] text-[#8B8B8B]">Loading simulation...</div>
  );
}
