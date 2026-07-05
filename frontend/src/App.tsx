import { useSimulation, useSimulationEvents } from "./hooks/useSimulation";
import { useWebSocket } from "./hooks/useWebSocket";
import { startSimulation } from "./lib/api";
import { SimForm } from "./components/simulation/SimForm";
import { PipelineProgress } from "./components/simulation/PipelineProgress";
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
      </main>
    </div>
  );
}
