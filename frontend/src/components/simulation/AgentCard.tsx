import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Badge } from "../common/Badge";
import type { AgentDecision } from "../../types";

interface Props {
  decision: AgentDecision;
  isNew?: boolean;
  actionMeta?: { is_terminal: boolean };
}

function getActionVariant(action: string, isTerminal?: boolean): "positive" | "negative" | "neutral" {
  if (isTerminal) return "negative";
  // Heuristic: common positive/negative keywords
  const lower = action.toLowerCase();
  if (["invest", "support", "approve", "accept", "adopt"].some(k => lower.includes(k))) return "positive";
  if (["reject", "pass", "divest", "oppose", "block"].some(k => lower.includes(k))) return "negative";
  return "neutral";
}

export function AgentCard({ decision, isNew, actionMeta }: Props) {
  const [expanded, setExpanded] = useState(false);

  const variant = getActionVariant(decision.action, actionMeta?.is_terminal);

  return (
    <div
      className={`border border-[#E5E5E5] rounded-[6px] bg-white transition-all duration-200 ${
        isNew ? "animate-fade-in" : ""
      } ${expanded ? "border-l-2 border-l-[#1A1A1A]" : ""}`}
    >
      {/* Compact view */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 text-left flex items-start justify-between gap-2"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[13px] font-medium text-[#0F0F0F] truncate">
              {decision.archetype}
            </span>
            {decision.cluster_id && (
              <Badge label={decision.cluster_id} size="sm" />
            )}
          </div>
          <div className="flex items-center gap-3">
            <Badge label={decision.action} variant={variant} />
            <span className="text-[13px] font-['JetBrains_Mono'] text-[#6B6B6B] tabular-nums">
              {decision.utility >= 0 ? "+" : ""}{decision.utility.toFixed(2)}
            </span>
          </div>
        </div>
        <ChevronDown
          size={14}
          className={`text-[#9B9B9B] mt-1 shrink-0 transition-transform duration-200 ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Expanded view */}
      {expanded && (
        <div className="px-3 pb-3 border-t border-[#E5E5E5] pt-3 space-y-3">
          {/* Utility dimensions */}
          {Object.keys(decision.utility_dimensions).length > 0 && (
            <div className="space-y-1.5">
              <span className="text-[11px] text-[#9B9B9B] uppercase tracking-wider">Dimensions</span>
              {Object.entries(decision.utility_dimensions).map(([dim, score]) => (
                <div key={dim} className="flex items-center gap-2">
                  <span className="text-[12px] text-[#6B6B6B] w-24 truncate">{dim}</span>
                  <div className="flex-1 h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        score >= 0 ? "bg-[#16653A]" : "bg-[#8B1A1A]"
                      }`}
                      style={{ width: `${Math.abs(score) * 50 + 50}%`, marginLeft: score < 0 ? "auto" : undefined }}
                    />
                  </div>
                  <span className="text-[11px] font-['JetBrains_Mono'] text-[#6B6B6B] w-10 text-right tabular-nums">
                    {score >= 0 ? "+" : ""}{score.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Reasoning chain */}
          {decision.reasoning_chain.length > 0 && (
            <div className="space-y-1">
              <span className="text-[11px] text-[#9B9B9B] uppercase tracking-wider">Reasoning</span>
              <ul className="space-y-1">
                {decision.reasoning_chain.map((step, i) => (
                  <li key={i} className="text-[12px] text-[#6B6B6B] leading-relaxed">
                    <span className="font-medium text-[#0F0F0F]">{step.dimension}</span>
                    <span className="font-['JetBrains_Mono'] text-[11px] ml-1">({step.score >= 0 ? "+" : ""}{step.score.toFixed(1)})</span>
                    {" — "}{step.reasoning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Emotional state */}
          {decision.new_state && (
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-[#9B9B9B] uppercase tracking-wider">State</span>
              <span className="text-[12px] text-[#6B6B6B]">{decision.new_state}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
