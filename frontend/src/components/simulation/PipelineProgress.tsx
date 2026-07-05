import type { PipelineStage } from "../../types";

const STAGES: { key: PipelineStage; label: string }[] = [
  { key: "schema", label: "Schema" },
  { key: "swarm", label: "Swarm" },
  { key: "round1", label: "R1" },
  { key: "round2", label: "R2" },
  { key: "round3", label: "R3" },
  { key: "report", label: "Report" },
];

interface Props {
  currentStage: PipelineStage | null;
  progress: number;
}

function getStageStatus(stage: PipelineStage, currentStage: PipelineStage | null): "complete" | "active" | "pending" {
  if (!currentStage) return "pending";
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);
  const stageIdx = STAGES.findIndex((s) => s.key === stage);
  if (stageIdx < currentIdx) return "complete";
  if (stageIdx === currentIdx) return "active";
  return "pending";
}

export function PipelineProgress({ currentStage, progress }: Props) {
  return (
    <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
      {/* Stage dots */}
      <div className="flex items-center justify-between mb-3">
        {STAGES.map((stage, i) => {
          const status = getStageStatus(stage.key, currentStage);
          return (
            <div key={stage.key} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`w-3 h-3 rounded-full transition-all duration-300 ${
                    status === "complete"
                      ? "bg-[#1A1A1A]"
                      : status === "active"
                      ? "bg-[#1A1A1A] animate-pulse"
                      : "border-2 border-[#D0D0D0] bg-transparent"
                  }`}
                />
                <span className="mt-1.5 text-[11px] text-[#9B9B9B]">{stage.label}</span>
              </div>
              {i < STAGES.length - 1 && (
                <div
                  className={`w-12 h-[1px] mx-2 transition-colors duration-300 ${
                    getStageStatus(STAGES[i + 1].key, currentStage) !== "pending"
                      ? "bg-[#1A1A1A]"
                      : "bg-[#E5E5E5]"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
      {/* Progress bar */}
      <div className="h-1 bg-[#E5E5E5] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#1A1A1A] rounded-full transition-[width] duration-300 ease-linear"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
