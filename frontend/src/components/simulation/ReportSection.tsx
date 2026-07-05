import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { ChevronDown } from "lucide-react";
import type { SimulationResult } from "../../types";

interface Props {
  result: SimulationResult;
}

function getVerdictStyle(verdict: string): { bg: string; text: string } {
  const v = verdict.toLowerCase();
  if (v.includes("resilient")) return { bg: "#ECFDF5", text: "#16653A" };
  if (v.includes("fragile")) return { bg: "#FEF2F2", text: "#8B1A1A" };
  return { bg: "#FEFCE8", text: "#6B5C1A" }; // moderate/indeterminate
}

export function ReportSection({ result }: Props) {
  const [showRaw, setShowRaw] = useState(false);

  const verdict = result.resilience_metrics?.verdict || result.verdict || "Unknown";
  const verdictStyle = getVerdictStyle(verdict);
  const stability = result.resilience_metrics?.decision_stability;
  const drift = result.resilience_metrics?.utility_drift_mean;

  return (
    <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4 space-y-4">
      {/* Verdict badge */}
      <div className="flex items-center gap-4">
        <span
          className="px-3 py-1.5 rounded-[6px] text-[14px] font-medium"
          style={{ backgroundColor: verdictStyle.bg, color: verdictStyle.text }}
        >
          {verdict}
        </span>
        {stability !== undefined && (
          <span className="text-[13px] text-[#6B6B6B]">
            Stability: <span className="font-['JetBrains_Mono'] text-[#0F0F0F]">{(stability * 100).toFixed(0)}%</span>
          </span>
        )}
        {drift !== undefined && (
          <span className="text-[13px] text-[#6B6B6B]">
            Drift: <span className="font-['JetBrains_Mono'] text-[#0F0F0F]">{drift >= 0 ? "+" : ""}{drift.toFixed(3)}</span>
          </span>
        )}
      </div>

      {/* Crisis event */}
      {result.crisis_event && (
        <div className="border-l-2 border-[#8B1A1A] pl-3">
          <span className="text-[11px] text-[#8B1A1A] uppercase tracking-wider font-medium">Crisis</span>
          <p className="text-[13px] text-[#0F0F0F] mt-0.5">{result.crisis_event}</p>
        </div>
      )}

      {/* Rendered markdown report */}
      {result.report_md && (
        <div className="prose prose-sm max-w-none text-[13px] leading-relaxed text-[#0F0F0F] [&_h1]:text-[16px] [&_h1]:font-medium [&_h1]:mt-4 [&_h1]:mb-2 [&_h2]:text-[14px] [&_h2]:font-medium [&_h2]:mt-3 [&_h2]:mb-1.5 [&_h3]:text-[13px] [&_h3]:font-medium [&_h3]:mt-2 [&_h3]:mb-1 [&_p]:mb-2 [&_ul]:pl-4 [&_li]:mb-0.5 [&_strong]:text-[#0F0F0F] [&_em]:text-[#6B6B6B] [&_blockquote]:border-l-2 [&_blockquote]:border-[#E5E5E5] [&_blockquote]:pl-3 [&_blockquote]:text-[#6B6B6B]">
          <ReactMarkdown>{result.report_md}</ReactMarkdown>
        </div>
      )}

      {/* Collapsible raw JSON */}
      <div className="border-t border-[#E5E5E5] pt-3">
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="flex items-center gap-1.5 text-[12px] text-[#9B9B9B] hover:text-[#6B6B6B] transition-colors"
        >
          <ChevronDown
            size={12}
            className={`transition-transform duration-200 ${showRaw ? "rotate-180" : ""}`}
          />
          Raw JSON
        </button>
        {showRaw && (
          <pre className="mt-2 p-3 bg-[#FAFAFA] border border-[#E5E5E5] rounded-[6px] text-[11px] font-['JetBrains_Mono'] text-[#6B6B6B] overflow-x-auto max-h-[400px] overflow-y-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </div>

      {/* Timing */}
      {result.timings && (
        <div className="flex gap-4 text-[12px] text-[#9B9B9B]">
          <span>Total: <span className="font-['JetBrains_Mono'] text-[#6B6B6B]">{result.timings.total.toFixed(1)}s</span></span>
          <span>R1: <span className="font-['JetBrains_Mono']">{result.timings.r1.toFixed(1)}s</span></span>
          <span>R2: <span className="font-['JetBrains_Mono']">{result.timings.r2.toFixed(1)}s</span></span>
          <span>R3: <span className="font-['JetBrains_Mono']">{result.timings.r3.toFixed(1)}s</span></span>
        </div>
      )}
    </div>
  );
}
