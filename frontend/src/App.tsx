import { useState, useEffect } from "react";
import { useSimulation, useSimulationEvents } from "./hooks/useSimulation";
import { useWebSocket } from "./hooks/useWebSocket";
import { startSimulation, approveSchema, cancelSimulation, getRunDetail } from "./lib/api";
import { Header } from "./components/layout/Header";
import { LandingHero } from "./components/layout/LandingHero";
import { SettingsPanel } from "./components/layout/SettingsPanel";
import { SimForm } from "./components/simulation/SimForm";
import { PipelineProgress } from "./components/simulation/PipelineProgress";
import { SchemaApproval } from "./components/simulation/SchemaApproval";
import { AgentCard } from "./components/simulation/AgentCard";
import { RoundTimeline } from "./components/simulation/RoundTimeline";
import { ResultsView } from "./components/simulation/ResultsView";
import { ConditionalTriggersPanel } from "./components/dynamics/ConditionalTriggersPanel";
import { HistoricalContextPanel } from "./components/dynamics/HistoricalContextPanel";
import type { SimulationConfig } from "./types";

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { state, dispatch } = useSimulation();
  const { events, status: wsStatus } = useWebSocket(state.runId);

  useSimulationEvents(dispatch, events);

  // Share link: load run from ?run=<id> on page load
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
    }
  }, []);

  const handleGetStarted = () => {
    setShowLanding(false);
  };

  const handleSubmit = async (config: SimulationConfig) => {
    setShowLanding(false);
    setSubmitError(null);
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
    // Clear URL params
    window.history.replaceState({}, "", window.location.pathname);
  };

  // Determine which round's agents to show as cards
  const latestRound = Math.max(...Object.keys(state.agentsByRound).map(Number), 0);
  const latestAgents = state.agentsByRound[latestRound] || [];

  // Build action metadata from schema
  const actionMeta: Record<string, { is_terminal: boolean }> = {};
  if (state.schema) {
    state.schema.actions.forEach((a) => {
      actionMeta[a.name] = { is_terminal: a.is_terminal };
    });
  }

  return (
    <div className="min-h-screen">
      <Header onOpenSettings={() => setShowSettings(true)} />
      <SettingsPanel open={showSettings} onClose={() => setShowSettings(false)} />

      <main className="mx-auto max-w-[960px] px-6 py-6 space-y-6">
        {/* Landing hero — shown until user clicks Get Started or starts a sim */}
        {showLanding && state.status === "idle" && (
          <LandingHero onGetStarted={handleGetStarted} />
        )}

        {state.status !== "complete" && !showLanding && (
          <SimForm
            onSubmit={handleSubmit}
            disabled={state.status === "running" || state.status === "schema_pending"}
          />
        )}

        {/* Submit error (rate limit, network, etc.) */}
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

        {state.status === "running" && (
          <div className="space-y-3">
            <PipelineProgress
              currentStage={state.currentStage}
              progress={state.progress}
              agentCount={state.agents.length || undefined}
              agentsCompleted={latestAgents.length || undefined}
              wsConnected={wsStatus === "connected"}
            />
            <div className="flex justify-end">
              <button
                onClick={handleCancel}
                className="px-4 py-1.5 text-[13px] font-medium text-[#8B1A1A] border border-[#8B1A1A]/30 rounded-[6px] hover:bg-[#FEF2F2] transition-colors"
              >
                Cancel Simulation
              </button>
            </div>
          </div>
        )}

        {state.status === "schema_pending" && state.schema && (
          <SchemaApproval
            schema={state.schema}
            onApprove={handleApproveSchema}
          />
        )}

        {state.status === "error" && (
          <div className="border border-[#8B1A1A]/20 rounded-[6px] bg-[#FEF2F2] p-4">
            <p className="text-[14px] text-[#8B1A1A]">{state.error}</p>
          </div>
        )}

        {/* Schema info (during running only) */}
        {state.schema && state.status !== "complete" && (
          <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
            <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-2">{state.schema.scenario_name}</h2>
            <div className="flex flex-wrap gap-2">
              {state.schema.evaluation_dimensions.map((dim) => (
                <span key={dim} className="px-2 py-0.5 text-[11px] bg-[#F5F5F5] text-[#6B6B6B] rounded-[4px]">
                  {dim}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* External events (during running) */}
        {state.stressEvent && state.status === "running" && (
          <div className="space-y-2">
            <div className="border border-[#8B1A1A]/20 rounded-[6px] bg-[#FEF2F2] p-4">
              <span className="text-[11px] text-[#8B1A1A] uppercase tracking-wider font-medium">Stress Event</span>
              <p className="text-[14px] text-[#0F0F0F] mt-1">{state.stressEvent}</p>
            </div>
            {state.validationEvent && (
              <div className="border border-[#166534]/20 rounded-[6px] bg-[#F0FDF4] p-4">
                <span className="text-[11px] text-[#166534] uppercase tracking-wider font-medium">Validation Event</span>
                <p className="text-[14px] text-[#0F0F0F] mt-1">{state.validationEvent}</p>
              </div>
            )}
          </div>
        )}

        {/* Historical precedents (during running) */}
        {state.historicalPrecedents.length > 0 && state.status === "running" && (
          <HistoricalContextPanel precedents={state.historicalPrecedents} />
        )}

        {/* Conditional triggers (during running) */}
        {state.triggersEvents.length > 0 && state.status === "running" && (
          <ConditionalTriggersPanel triggers={state.triggersEvents} />
        )}

        {/* Agent cards grid */}
        {latestAgents.length > 0 && state.status === "running" && (
          <div>
            <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-3">
              Agents
              <span className="text-[#9B9B9B] font-normal ml-2 text-[13px]">Round {latestRound}</span>
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {latestAgents.map((d, i) => (
                <AgentCard
                  key={`${d.id}-${latestRound}`}
                  decision={d}
                  isNew={i === latestAgents.length - 1}
                  actionMeta={actionMeta[d.action]}
                  index={i}
                />
              ))}
            </div>
          </div>
        )}

        {/* Round timeline (during running) */}
        {Object.keys(state.agentsByRound).length > 0 && state.status === "running" && (
          <div>
            <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-3">Rounds</h2>
            <RoundTimeline
              rounds={state.rounds}
              agentsByRound={state.agentsByRound}
            />
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
