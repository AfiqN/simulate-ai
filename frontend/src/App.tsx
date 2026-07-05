import { useSimulation, useSimulationEvents } from "./hooks/useSimulation";
import { useWebSocket } from "./hooks/useWebSocket";
import { startSimulation } from "./lib/api";
import { SimForm } from "./components/simulation/SimForm";
import { PipelineProgress } from "./components/simulation/PipelineProgress";
import { AgentCard } from "./components/simulation/AgentCard";
import { RoundTimeline } from "./components/simulation/RoundTimeline";
import type { SimulationConfig } from "./types";

export default function App() {
  const { state, dispatch } = useSimulation();
  const { events } = useWebSocket(state.runId);

  useSimulationEvents(dispatch, events);

  const handleSubmit = async (config: SimulationConfig) => {
    try {
      const { id } = await startSimulation(config);
      dispatch({ type: "START", runId: id });
    } catch (err) {
      console.error("Failed to start simulation:", err);
    }
  };

  // Determine which round's agents to show as cards (latest active round)
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
      <header className="border-b border-[#E5E5E5] px-6 py-4">
        <h1 className="text-[20px] font-medium tracking-[-0.02em]">SimulateAI</h1>
      </header>
      <main className="mx-auto max-w-[960px] px-6 py-6 space-y-6">
        <SimForm
          onSubmit={handleSubmit}
          disabled={state.status === "running"}
        />

        {state.status !== "idle" && (
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

        {/* Crisis event */}
        {state.crisisEvent && (
          <div className="border border-[#8B1A1A]/20 rounded-[6px] bg-[#FEF2F2] p-4">
            <span className="text-[11px] text-[#8B1A1A] uppercase tracking-wider font-medium">Crisis Event</span>
            <p className="text-[14px] text-[#0F0F0F] mt-1">{state.crisisEvent}</p>
          </div>
        )}

        {/* Agent cards grid */}
        {latestAgents.length > 0 && (
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
      </main>
    </div>
  );
}
