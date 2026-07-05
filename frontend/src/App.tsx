import { useState } from "react";
import { useSimulation, useSimulationEvents } from "./hooks/useSimulation";
import { useWebSocket } from "./hooks/useWebSocket";
import { startSimulation } from "./lib/api";
import { Header } from "./components/layout/Header";
import { HistoryList } from "./components/layout/HistoryList";
import { SimForm } from "./components/simulation/SimForm";
import { PipelineProgress } from "./components/simulation/PipelineProgress";
import { AgentCard } from "./components/simulation/AgentCard";
import { RoundTimeline } from "./components/simulation/RoundTimeline";
import { ReportSection } from "./components/simulation/ReportSection";
import { VoteTally } from "./components/metrics/VoteTally";
import { ConsensusGauge } from "./components/metrics/ConsensusGauge";
import { DimensionChart } from "./components/metrics/DimensionChart";
import { SwingTable } from "./components/metrics/SwingTable";
import type { SimulationConfig, SimulationResult } from "./types";

function computeHHI(voteTally: Record<string, number>, totalAgents: number): number {
  if (totalAgents === 0) return 0;
  const shares = Object.values(voteTally).map((count) => count / totalAgents);
  return shares.reduce((sum, s) => sum + s * s, 0);
}

export default function App() {
  const [showHistory, setShowHistory] = useState(false);
  const { state, dispatch } = useSimulation();
  const { events } = useWebSocket(state.runId);

  useSimulationEvents(dispatch, events);

  const handleSubmit = async (config: SimulationConfig) => {
    setShowHistory(false);
    try {
      const { id } = await startSimulation(config);
      dispatch({ type: "START", runId: id });
    } catch (err) {
      console.error("Failed to start simulation:", err);
    }
  };

  const handleLoadResult = (result: SimulationResult) => {
    dispatch({ type: "LOAD_RESULT", result });
    setShowHistory(false);
  };

  const handleReset = () => {
    dispatch({ type: "RESET" });
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
      <Header showHistory={showHistory} onToggleHistory={() => setShowHistory(!showHistory)} />

      <main className="mx-auto max-w-[960px] px-6 py-6 space-y-6">
        {/* History view */}
        {showHistory && (
          <HistoryList onLoadResult={handleLoadResult} />
        )}

        {/* Simulation view */}
        {!showHistory && (
          <>
            {state.status !== "complete" && (
              <SimForm
                onSubmit={handleSubmit}
                disabled={state.status === "running"}
              />
            )}

            {state.status === "complete" && (
              <button
                onClick={handleReset}
                className="px-4 py-2 text-[13px] border border-[#E5E5E5] rounded-[6px] text-[#6B6B6B] hover:border-[#D0D0D0] hover:text-[#0F0F0F] transition-colors"
              >
                ← New Simulation
              </button>
            )}

            {state.status === "running" && (
              <PipelineProgress
                currentStage={state.currentStage}
                progress={state.progress}
              />
            )}

            {state.status === "error" && (
              <div className="border border-[#8B1A1A]/20 rounded-[6px] bg-[#FEF2F2] p-4">
                <p className="text-[14px] text-[#8B1A1A]">{state.error}</p>
              </div>
            )}

            {/* Schema info */}
            {state.schema && (
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
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Round timeline */}
            {Object.keys(state.agentsByRound).length > 0 && (
              <div>
                <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-3">Rounds</h2>
                <RoundTimeline
                  rounds={state.rounds}
                  agentsByRound={state.agentsByRound}
                />
              </div>
            )}

            {/* Metrics Dashboard */}
            {state.status === "complete" && state.result && (
              <div>
                <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-3">Metrics</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <VoteTally rounds={state.rounds} />
                  <ConsensusGauge
                    rounds={state.rounds.map((r) => ({
                      round: r.round,
                      hhi: r.consensus_index ?? computeHHI(r.vote_tally, r.decisions?.length || 0),
                    }))}
                  />
                  {state.result.quantitative_metrics?.dimension_stats && (
                    <DimensionChart stats={state.result.quantitative_metrics.dimension_stats} />
                  )}
                  {state.result.quantitative_metrics?.swing_analysis && (
                    <SwingTable swings={state.result.quantitative_metrics.swing_analysis} />
                  )}
                </div>
              </div>
            )}

            {/* Report */}
            {state.status === "complete" && state.result && (
              <div>
                <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-3">Report</h2>
                <ReportSection result={state.result} />
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
