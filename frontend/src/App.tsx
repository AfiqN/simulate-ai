import { useState, useEffect, lazy, Suspense } from "react";
import { useSimulation, useSimulationEvents, getPersistedRun } from "./hooks/useSimulation";
import { useWebSocket } from "./hooks/useWebSocket";
import { useNotification } from "./hooks/useNotification";
import { useDocumentTitle } from "./hooks/useDocumentTitle";
import { startSimulation, approveSchema, cancelSimulation, getRunDetail } from "./lib/api";
import { Header } from "./components/layout/Header";
import { LandingHero } from "./components/layout/LandingHero";
import { SettingsPanel } from "./components/layout/SettingsPanel";
import { SimForm } from "./components/simulation/SimForm";
import { SimulationLive } from "./components/simulation/SimulationLive";
import type { SimulationConfig } from "./types";
import type { ExampleData } from "./lib/transformMetrics";

// Lazy-loaded: only needed after simulation completes or during schema gate
const ResultsView = lazy(() => import("./components/simulation/ResultsView").then(m => ({ default: m.ResultsView })));
const SchemaApproval = lazy(() => import("./components/simulation/SchemaApproval").then(m => ({ default: m.SchemaApproval })));

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastStimulus, setLastStimulus] = useState("");
  const [lastDepth, setLastDepth] = useState<string>("standard");
  const [startedAt, setStartedAt] = useState<number | undefined>(undefined);
  const { state, dispatch } = useSimulation();
  const { events, status: wsStatus } = useWebSocket(state.runId);
  const { notify } = useNotification();

  useSimulationEvents(dispatch, events);
  useDocumentTitle(state.status, state.progress);

  // Recover active run from localStorage on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const runId = params.get("run");

    if (runId) {
      setShowLanding(false);
      getRunDetail(runId).then((data) => {
        if (data.status === "completed" && data.result) {
          dispatch({ type: "LOAD_RESULT", result: data.result });
        }
      }).catch(() => {});
      return;
    }

    // Check localStorage for an in-progress run
    const persisted = getPersistedRun();
    if (persisted) {
      setShowLanding(false);
      getRunDetail(persisted.runId).then((data) => {
        if (data.status === "completed" && data.result) {
          dispatch({ type: "LOAD_RESULT", result: data.result });
        } else if (data.status === "running" || data.status === "queued") {
          // Reconnect with progress from backend
          dispatch({ type: "RECOVER", runId: persisted.runId, progress: data.progress ?? 0, stage: data.stage });
          setLastDepth(persisted.depth || "standard");
          setStartedAt(persisted.startedAt);
          if (persisted.stimulus) setLastStimulus(persisted.stimulus);
        }
      }).catch(() => {
        // Run not found — clear stale entry
        dispatch({ type: "RESET" });
        try { localStorage.removeItem("simulate-ai-active-run"); } catch {}
      });
    }
  }, []);

  // Fire browser notification on completion/error
  useEffect(() => {
    if (state.status === "complete" && state.result) {
      const verdict = state.result.verdict || "Done";
      notify("Simulation complete", `Verdict: ${verdict}`);
    } else if (state.status === "error") {
      notify("Simulation failed", state.error || "An error occurred");
    }
  }, [state.status]);

  const handleGetStarted = () => {
    setShowLanding(false);
  };

  const handleSubmit = async (config: SimulationConfig) => {
    setShowLanding(false);
    setSubmitError(null);
    setLastStimulus(config.stimulus);
    setLastDepth(config.depth);
    setStartedAt(Date.now());
    try {
      const { id } = await startSimulation(config);
      dispatch({ type: "START", runId: id });
      // Persist with depth and stimulus for recovery
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
    } catch (err) {
      console.error("Failed to cancel simulation:", err);
    }
  };

  const handleReset = () => {
    dispatch({ type: "RESET" });
    setShowLanding(true);
    setSubmitError(null);
    window.history.replaceState({}, "", window.location.pathname);
    // Clear persisted run so refresh doesn't try to recover
    try { localStorage.removeItem("simulate-ai-active-run"); } catch {}
  };

  const handleLoadExample = (data: ExampleData) => {
    setShowLanding(false);
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
  };

  const latestRound = Math.max(...Object.keys(state.agentsByRound).map(Number), 0);
  const latestAgents = state.agentsByRound[latestRound] || [];

  return (
    <div className="min-h-screen">
      <Header onOpenSettings={() => setShowSettings(true)} onLogoClick={handleReset} />
      <SettingsPanel open={showSettings} onClose={() => setShowSettings(false)} />

      <main className="mx-auto max-w-[960px] px-6 py-6 space-y-6">
        {/* Landing hero */}
        {showLanding && state.status === "idle" && (
          <LandingHero onGetStarted={handleGetStarted} onLoadExample={handleLoadExample} />
        )}

        {/* Form — hidden during running/complete */}
        {state.status !== "complete" && state.status !== "running" && !showLanding && (
          <SimForm
            onSubmit={handleSubmit}
            disabled={state.status === "schema_pending"}
          />
        )}

        {/* Submit error */}
        {submitError && state.status === "idle" && (
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

        {/* Schema approval */}
        {state.status === "schema_pending" && state.schema && (
          <Suspense fallback={<div className="py-10 text-center text-[13px] text-[#8B8B8B]">Loading...</div>}>
            <SchemaApproval
              schema={state.schema}
              onApprove={handleApproveSchema}
            />
          </Suspense>
        )}

        {/* Running — immersive live view */}
        {state.status === "running" && (
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
            onCancel={handleCancel}
          />
        )}

        {/* Error */}
        {state.status === "error" && (
          <div className="border border-[#8B1A1A]/20 rounded-[6px] bg-[#FEF2F2] p-4">
            <p className="text-[14px] text-[#8B1A1A]">{state.error}</p>
            <button
              onClick={handleReset}
              className="mt-3 text-[13px] text-[#8B1A1A] underline"
            >
              Start over
            </button>
          </div>
        )}

        {/* Complete: Full results view */}
        {state.status === "complete" && state.result && (
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
              runId={state.runId || undefined}
              onReset={handleReset}
            />
          </Suspense>
        )}
      </main>
    </div>
  );
}
