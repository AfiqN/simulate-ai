import { useState, useEffect } from "react";
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
import { SchemaApproval } from "./components/simulation/SchemaApproval";
import { ResultsView } from "./components/simulation/ResultsView";
import type { SimulationConfig } from "./types";

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastStimulus, setLastStimulus] = useState("");
  const [lastDepth, setLastDepth] = useState<string>("standard");
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
          // Reconnect to the live simulation
          dispatch({ type: "START", runId: persisted.runId });
        }
      }).catch(() => {
        // Run not found — clear stale entry
        dispatch({ type: "RESET" });
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
    try {
      const { id } = await startSimulation(config);
      dispatch({ type: "START", runId: id });
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
  };

  const latestRound = Math.max(...Object.keys(state.agentsByRound).map(Number), 0);
  const latestAgents = state.agentsByRound[latestRound] || [];

  return (
    <div className="min-h-screen">
      <Header onOpenSettings={() => setShowSettings(true)} />
      <SettingsPanel open={showSettings} onClose={() => setShowSettings(false)} />

      <main className="mx-auto max-w-[960px] px-6 py-6 space-y-6">
        {/* Landing hero */}
        {showLanding && state.status === "idle" && (
          <LandingHero onGetStarted={handleGetStarted} />
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
          <SchemaApproval
            schema={state.schema}
            onApprove={handleApproveSchema}
          />
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
        )}
      </main>
    </div>
  );
}
