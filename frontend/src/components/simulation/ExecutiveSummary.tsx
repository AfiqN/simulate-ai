import { Download, Clock, Users, TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { SimulationResult, RoundSummary } from "../../types";

interface Props {
  result: SimulationResult;
  rounds: RoundSummary[];
  scenarioName?: string;
  onExportPdf: () => void;
  exporting?: boolean;
}

function getVerdictStyle(verdict: string) {
  const v = verdict.toLowerCase();
  if (v.includes("resilient")) return { bg: "#ECFDF5", text: "#16653A", border: "#16653A" };
  if (v.includes("fragile")) return { bg: "#FEF2F2", text: "#8B1A1A", border: "#8B1A1A" };
  return { bg: "#FEFCE8", text: "#6B5C1A", border: "#6B5C1A" };
}

function getHHILabel(hhi: number): string {
  if (hhi >= 0.7) return "Aligned";
  if (hhi >= 0.4) return "Converging";
  return "Fragmented";
}

export function ExecutiveSummary({ result, rounds, scenarioName, onExportPdf, exporting }: Props) {
  const verdict = result.resilience_metrics?.verdict || result.verdict || "Unknown";
  const verdictStyle = getVerdictStyle(verdict);
  const stability = result.resilience_metrics?.decision_stability;
  const drift = result.resilience_metrics?.utility_drift_mean;

  // Compute latest HHI
  const latestRound = rounds[rounds.length - 1];
  const latestHHI = latestRound?.consensus_index ??
    (result.quantitative_metrics?.consensus_index
      ? Object.values(result.quantitative_metrics.consensus_index).pop()
      : undefined);

  // Total agents from latest round
  const totalAgents = latestRound?.decisions?.length || 0;

  return (
    <div className="border border-[#E5E5E5] rounded-[8px] bg-white overflow-hidden">
      {/* Top color accent bar */}
      <div className="h-1" style={{ backgroundColor: verdictStyle.border }} />

      <div className="p-6">
        {/* Header row: title + export button */}
        <div className="flex items-start justify-between mb-5">
          <div>
            <h1 className="text-[18px] font-semibold tracking-[-0.02em] text-[#0F0F0F] mb-1">
              {scenarioName || result.scenario_name || "Simulation Report"}
            </h1>
            <p className="text-[13px] text-[#9B9B9B]">
              {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
            </p>
          </div>
          <button
            onClick={onExportPdf}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 bg-[#0F0F0F] text-white text-[13px] font-medium rounded-[6px] hover:bg-[#2A2A2A] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download size={14} />
            {exporting ? "Exporting…" : "Export PDF"}
          </button>
        </div>

        {/* Verdict + Metrics row */}
        <div className="flex flex-wrap items-center gap-6">
          {/* Verdict badge - large */}
          <div
            className="px-4 py-2 rounded-[8px] border"
            style={{ backgroundColor: verdictStyle.bg, borderColor: verdictStyle.border + "40", color: verdictStyle.text }}
          >
            <span className="text-[11px] uppercase tracking-wider font-medium block opacity-70">Verdict</span>
            <span className="text-[20px] font-semibold">{verdict}</span>
          </div>

          {/* Metric pills */}
          <div className="flex flex-wrap gap-4">
            {stability !== undefined && (
              <MetricPill
                label="Stability"
                value={`${(stability * 100).toFixed(0)}%`}
                icon={stability >= 0.7 ? <TrendingUp size={13} /> : stability >= 0.4 ? <Minus size={13} /> : <TrendingDown size={13} />}
              />
            )}
            {drift !== undefined && (
              <MetricPill
                label="Drift"
                value={`${drift >= 0 ? "+" : ""}${drift.toFixed(3)}`}
                icon={drift > 0 ? <TrendingUp size={13} /> : drift < 0 ? <TrendingDown size={13} /> : <Minus size={13} />}
              />
            )}
            {latestHHI !== undefined && (
              <MetricPill
                label={`HHI (${getHHILabel(latestHHI)})`}
                value={latestHHI.toFixed(2)}
              />
            )}
            {totalAgents > 0 && (
              <MetricPill
                label="Agents"
                value={String(totalAgents)}
                icon={<Users size={13} />}
              />
            )}
            {result.timings?.total && (
              <MetricPill
                label="Duration"
                value={`${result.timings.total.toFixed(1)}s`}
                icon={<Clock size={13} />}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricPill({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-[#9B9B9B] uppercase tracking-wider">{label}</span>
      <div className="flex items-center gap-1 mt-0.5">
        {icon && <span className="text-[#6B6B6B]">{icon}</span>}
        <span className="text-[16px] font-['JetBrains_Mono'] font-medium text-[#0F0F0F] tabular-nums">{value}</span>
      </div>
    </div>
  );
}
