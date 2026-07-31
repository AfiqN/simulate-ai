import { useState, useEffect, useRef } from "react";
import type { PipelineStage, AgentDecision } from "../../types";

interface Props {
  currentStage: PipelineStage | null;
  progress: number;
  agentCount?: number;
  agents: { id: string; archetype: string; cluster_id: string }[];
  latestAgents: AgentDecision[];
  latestRound: number;
  stimulus?: string;
  depth?: string;
  startedAt?: number;
  wsConnected: boolean;
  onCancel: () => void;
}

const STAGES: { key: PipelineStage; short: string }[] = [
  { key: "schema", short: "Schema" },
  { key: "swarm", short: "Swarm" },
  { key: "round1", short: "R1" },
  { key: "round2", short: "R2" },
  { key: "round3", short: "R3" },
  { key: "report", short: "Report" },
];

const STAGE_META: Record<string, { label: string; verb: string }> = {
  schema: { label: "Schema Design", verb: "Designing scenario architecture" },
  swarm: { label: "Agent Generation", verb: "Recruiting agent personas" },
  round1: { label: "Round 1 — Perception", verb: "Agents forming initial positions" },
  round2: { label: "Round 2 — Debate", verb: "Agents challenging each other" },
  round3: { label: "Round 3 — Crisis", verb: "Agents reacting to stress event" },
  round4: { label: "Round 4 — Stabilization", verb: "Agents reaching final positions" },
  report: { label: "Synthesis", verb: "Compiling diagnostic report" },
};

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function ThinkingDot({ delay }: { delay: number }) {
  return (
    <span
      className="inline-block w-[4px] h-[4px] bg-current rounded-full animate-[thinking_1.4s_ease-in-out_infinite]"
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}

function AgentThinkingRow({ name, status, action }: { name: string; status: "thinking" | "done"; action?: string }) {
  return (
    <div className={`flex items-center gap-3 py-2.5 px-3 rounded-[6px] transition-colors duration-300 ${status === "done" ? "bg-[#FAFAFA]" : ""}`}>
      <div className={`w-[6px] h-[6px] rounded-full transition-all duration-500 ${status === "done" ? "bg-[#0F0F0F] scale-100" : "bg-[#D0D0D0] scale-75"}`} />
      <span className={`text-[13px] flex-1 truncate transition-colors duration-300 ${status === "done" ? "text-[#0F0F0F]" : "text-[#8B8B8B]"}`}>
        {name}
      </span>
      {status === "thinking" ? (
        <div className="flex gap-[3px] text-[#8B8B8B]">
          <ThinkingDot delay={0} />
          <ThinkingDot delay={200} />
          <ThinkingDot delay={400} />
        </div>
      ) : (
        <span className="text-[11px] text-[#8B8B8B] font-['JetBrains_Mono']">
          {action || "done"}
        </span>
      )}
    </div>
  );
}

function StageBreadcrumb({ currentStage }: { currentStage: PipelineStage | null }) {
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);

  return (
    <div className="flex items-center gap-1">
      {STAGES.map((stage, i) => {
        const isComplete = i < currentIdx;
        const isActive = i === currentIdx;
        return (
          <div key={stage.key} className="flex items-center gap-1">
            <div
              className={`h-[4px] rounded-full transition-all duration-500 ${
                isComplete
                  ? "w-[20px] bg-white"
                  : isActive
                  ? "w-[32px] bg-white"
                  : "w-[12px] bg-[#3A3A3A]"
              }`}
            />
          </div>
        );
      })}
    </div>
  );
}

// Estimated total time in seconds by depth
const ESTIMATE_BY_DEPTH: Record<string, number> = {
  quick: 180,    // ~3 min
  standard: 300, // ~5 min
  deep: 480,     // ~8 min
};

function formatEstimate(seconds: number): string {
  if (seconds <= 0) return "almost done";
  const m = Math.ceil(seconds / 60);
  if (m <= 1) return "< 1 min left";
  return `~${m} min left`;
}

export function SimulationLive({ currentStage, progress, agents, latestAgents, latestRound, stimulus, depth, startedAt, wsConnected, onCancel }: Props) {
  const [elapsed, setElapsed] = useState(() => {
    if (startedAt) return Math.floor((Date.now() - startedAt) / 1000);
    return 0;
  });
  const [activityLog, setActivityLog] = useState<string[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);
  const prevStageRef = useRef<PipelineStage | null>(null);

  useEffect(() => {
    const interval = setInterval(() => setElapsed((p) => p + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (currentStage && currentStage !== prevStageRef.current) {
      const meta = STAGE_META[currentStage];
      if (meta) {
        setActivityLog((prev) => [...prev, meta.verb]);
      }
      prevStageRef.current = currentStage;
    }
  }, [currentStage]);

  useEffect(() => {
    if (latestAgents.length > 0) {
      const last = latestAgents[latestAgents.length - 1];
      setActivityLog((prev) => {
        const msg = `${last.archetype} → ${last.action}`;
        if (prev[prev.length - 1] === msg) return prev;
        return [...prev.slice(-20), msg];
      });
    }
  }, [latestAgents]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activityLog]);

  const stageMeta = currentStage ? STAGE_META[currentStage] : null;
  const isRoundStage = currentStage?.startsWith("round");

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Main status card */}
      <div className="bg-[#0F0F0F] rounded-[12px] p-6 sm:p-8 text-white overflow-hidden relative">
        {/* Subtle animated bg shimmer */}
        <div className="absolute inset-0 opacity-[0.03]">
          <div className="absolute inset-0 animate-[shimmer_3s_ease-in-out_infinite] bg-[linear-gradient(110deg,transparent_25%,rgba(255,255,255,0.4)_50%,transparent_75%)] bg-[length:200%_100%]" />
        </div>

        <div className="relative">
          {/* Top bar */}
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-[#6B6B6B] uppercase tracking-wider font-['JetBrains_Mono']">
                {wsConnected ? "Running" : "Reconnecting..."}
              </span>
              {!wsConnected && (
                <div className="w-[6px] h-[6px] rounded-full bg-[#6B6B6B] animate-pulse" />
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-[13px] text-[#6B6B6B] font-['JetBrains_Mono'] tabular-nums">
                {formatElapsed(elapsed)}
              </span>
              {depth && (
                <span className="text-[11px] text-[#505050] font-['JetBrains_Mono']">
                  · {formatEstimate(Math.max(0, (ESTIMATE_BY_DEPTH[depth] || 300) - elapsed))}
                </span>
              )}
            </div>
          </div>

          {/* Stage verb */}
          <div className="mb-5">
            <p className="text-[11px] text-[#6B6B6B] uppercase tracking-wider mb-1.5 font-['JetBrains_Mono']">
              {stageMeta?.label || "Initializing"}
            </p>
            <p className="text-[20px] sm:text-[24px] font-medium tracking-[-0.02em] leading-tight">
              {stageMeta?.verb || "Setting up simulation..."}
            </p>
            {stimulus && (
              <p className="text-[13px] text-[#6B6B6B] mt-2 truncate max-w-[90%]">
                "{stimulus}"
              </p>
            )}
          </div>

          {/* Stage breadcrumb */}
          <div className="mb-4">
            <StageBreadcrumb currentStage={currentStage} />
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <div className="h-[2px] bg-[#2A2A2A] rounded-full overflow-hidden">
              <div
                className="h-full bg-white rounded-full transition-[width] duration-700 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="flex justify-between text-[11px] text-[#505050] font-['JetBrains_Mono']">
              <span>{Math.round(progress)}%</span>
              {isRoundStage && agents.length > 0 && (
                <span>{latestAgents.length}/{agents.length} agents complete</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Agent panel */}
        <div className="border border-[#E5E5E5] rounded-[10px] bg-white overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#F0F0F0]">
            <h3 className="text-[12px] text-[#8B8B8B] uppercase tracking-wider font-medium">
              Agents {isRoundStage && latestRound > 0 && `· Round ${latestRound}`}
            </h3>
            {agents.length > 0 && (
              <span className="text-[11px] text-[#B0B0B0] font-['JetBrains_Mono']">
                {latestAgents.length}/{agents.length}
              </span>
            )}
          </div>

          <div className="p-2 max-h-[300px] overflow-y-auto">
            {agents.length === 0 ? (
              <div className="py-10 text-center">
                <div className="flex justify-center gap-[3px] mb-3 text-[#8B8B8B]">
                  <ThinkingDot delay={0} />
                  <ThinkingDot delay={200} />
                  <ThinkingDot delay={400} />
                </div>
                <p className="text-[12px] text-[#8B8B8B]">Generating personas...</p>
              </div>
            ) : (
              agents.map((agent) => {
                const done = latestAgents.find((d) => d.id === agent.id || d.archetype === agent.archetype);
                return (
                  <AgentThinkingRow
                    key={agent.id}
                    name={agent.archetype}
                    status={done ? "done" : isRoundStage ? "thinking" : "done"}
                    action={done?.action}
                  />
                );
              })
            )}
          </div>
        </div>

        {/* Activity feed */}
        <div className="border border-[#E5E5E5] rounded-[10px] bg-white overflow-hidden">
          <div className="px-4 py-3 border-b border-[#F0F0F0]">
            <h3 className="text-[12px] text-[#8B8B8B] uppercase tracking-wider font-medium">
              Activity
            </h3>
          </div>

          <div className="p-4 max-h-[300px] overflow-y-auto font-['JetBrains_Mono']">
            {activityLog.length === 0 ? (
              <p className="text-[12px] text-[#B0B0B0] py-10 text-center">Waiting for events...</p>
            ) : (
              <div className="space-y-2">
                {activityLog.map((msg, i) => (
                  <div key={i} className="flex items-start gap-2.5 animate-slide-up" style={{ animationDelay: `${i * 30}ms` }}>
                    <span className="text-[10px] text-[#D0D0D0] mt-0.5 shrink-0 tabular-nums select-none">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className={`text-[12px] leading-snug ${i === activityLog.length - 1 ? "text-[#0F0F0F]" : "text-[#6B6B6B]"}`}>
                      {msg}
                    </span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cancel */}
      <div className="flex justify-end">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-[13px] text-[#8B8B8B] hover:text-[#0F0F0F] border border-[#E5E5E5] hover:border-[#D0D0D0] rounded-[6px] transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
