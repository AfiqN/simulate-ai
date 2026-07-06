import { useState, useEffect, useRef } from "react";
import { Wifi, WifiOff, Loader2 } from "lucide-react";
import type { PipelineStage } from "../../types";

const STAGES: { key: PipelineStage; label: string; description: string }[] = [
  { key: "schema", label: "Schema", description: "Generating scenario schema" },
  { key: "swarm", label: "Swarm", description: "Creating agent personas" },
  { key: "round1", label: "R1", description: "Round 1 — Initial decisions" },
  { key: "round2", label: "R2", description: "Round 2 — Post-crisis response" },
  { key: "round3", label: "R3", description: "Round 3 — Final positions" },
  { key: "round4", label: "R4", description: "Round 4 — Stabilization" },
  { key: "report", label: "Report", description: "Generating analysis report" },
];

interface Props {
  currentStage: PipelineStage | null;
  progress: number;
  agentCount?: number;
  agentsCompleted?: number;
  wsConnected?: boolean;
}

function getStageStatus(stage: PipelineStage, currentStage: PipelineStage | null): "complete" | "active" | "pending" {
  if (!currentStage) return "pending";
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);
  const stageIdx = STAGES.findIndex((s) => s.key === stage);
  if (stageIdx < currentIdx) return "complete";
  if (stageIdx === currentIdx) return "active";
  return "pending";
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s}s`;
}

export function PipelineProgress({ currentStage, progress, agentCount, agentsCompleted, wsConnected = true }: Props) {
  const [elapsed, setElapsed] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Elapsed timer
  useEffect(() => {
    if (currentStage) {
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [currentStage]);

  // Reset elapsed when stage resets
  useEffect(() => {
    if (!currentStage) setElapsed(0);
  }, [currentStage]);

  // Current stage description
  const activeStage = STAGES.find((s) => s.key === currentStage);

  return (
    <div className="border border-[#E5E5E5] rounded-[8px] bg-white p-5">
      {/* Header: description + elapsed + connection */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Loader2 size={14} className="text-[#2563EB] animate-spin" />
          <span className="text-[13px] text-[#0F0F0F] font-medium">
            {activeStage?.description || "Initializing…"}
          </span>
          {/* Agent progress during rounds */}
          {agentCount && agentsCompleted !== undefined && currentStage?.startsWith("round") && (
            <span className="text-[12px] text-[#9B9B9B] font-['JetBrains_Mono'] tabular-nums">
              {agentsCompleted}/{agentCount} agents
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[12px] text-[#9B9B9B] font-['JetBrains_Mono'] tabular-nums">
            {formatElapsed(elapsed)}
          </span>
          {/* WS connection indicator */}
          <div className="flex items-center gap-1">
            {wsConnected ? (
              <Wifi size={12} className="text-[#16653A]" />
            ) : (
              <WifiOff size={12} className="text-[#8B1A1A]" />
            )}
            <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? "bg-[#16653A]" : "bg-[#8B1A1A] animate-pulse"}`} />
          </div>
        </div>
      </div>

      {/* Stage dots */}
      <div className="flex items-center justify-between mb-3">
        {STAGES.map((stage, i) => {
          const status = getStageStatus(stage.key, currentStage);
          return (
            <div key={stage.key} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`w-3 h-3 rounded-full transition-all duration-500 ${
                    status === "complete"
                      ? "bg-[#16653A] scale-100"
                      : status === "active"
                      ? "bg-[#2563EB] animate-pulse scale-110"
                      : "border-2 border-[#D0D0D0] bg-transparent"
                  }`}
                />
                <span className={`mt-1.5 text-[11px] transition-colors duration-300 ${
                  status === "active" ? "text-[#2563EB] font-medium" :
                  status === "complete" ? "text-[#16653A]" : "text-[#9B9B9B]"
                }`}>
                  {stage.label}
                </span>
              </div>
              {i < STAGES.length - 1 && (
                <div
                  className={`w-12 h-[1.5px] mx-2 transition-all duration-500 ${
                    getStageStatus(STAGES[i + 1].key, currentStage) !== "pending"
                      ? "bg-[#16653A]"
                      : getStageStatus(stage.key, currentStage) === "active"
                      ? "bg-gradient-to-r from-[#2563EB] to-[#E5E5E5]"
                      : "bg-[#E5E5E5]"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-[#2563EB] to-[#16653A] rounded-full transition-[width] duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
