import { useState } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Badge } from "../common/Badge";
import type { AgentDecision, RoundSummary } from "../../types";

interface Props {
  rounds: RoundSummary[];
  agentsByRound: Record<number, AgentDecision[]>;
}

export function RoundTimeline({ rounds: _rounds, agentsByRound }: Props) {
  const availableRounds = Object.keys(agentsByRound).map(Number).sort();
  const [activeRound, setActiveRound] = useState(availableRounds[0] || 1);

  const currentDecisions = agentsByRound[activeRound] || [];
  const prevDecisions = activeRound > 1 ? (agentsByRound[activeRound - 1] || []) : [];

  // Build lookup for previous round
  const prevByAgent: Record<string, AgentDecision> = {};
  prevDecisions.forEach((d) => { prevByAgent[d.id] = d; });

  if (availableRounds.length === 0) return null;

  return (
    <div className="border border-[#E5E5E5] rounded-[6px] bg-white">
      {/* Tabs */}
      <div className="flex border-b border-[#E5E5E5]">
        {availableRounds.map((round) => (
          <button
            key={round}
            onClick={() => setActiveRound(round)}
            className={`px-4 py-2.5 text-[13px] font-medium transition-colors ${
              activeRound === round
                ? "text-[#0F0F0F] border-b-2 border-[#1A1A1A] -mb-[1px]"
                : "text-[#9B9B9B] hover:text-[#6B6B6B]"
            }`}
          >
            R{round}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-[#E5E5E5]">
              <th className="text-left px-4 py-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">Agent</th>
              <th className="text-left px-4 py-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">Action</th>
              <th className="text-right px-4 py-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">Utility</th>
              <th className="text-left px-4 py-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">State</th>
              <th className="text-left px-4 py-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">Reasoning</th>
            </tr>
          </thead>
          <tbody>
            {currentDecisions.map((d) => {
              const prev = prevByAgent[d.id];
              const flipped = prev && prev.action !== d.action;
              const utilityDelta = prev ? d.utility - prev.utility : 0;

              return (
                <tr
                  key={d.id}
                  className={`border-b border-[#E5E5E5] last:border-b-0 ${
                    flipped ? "border-l-2 border-l-[#2563EB]" : ""
                  }`}
                >
                  <td className="px-4 py-2.5 font-medium text-[#0F0F0F]">{d.archetype}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1.5">
                      <Badge
                        label={d.action}
                        variant={flipped ? "shift" : "default"}
                      />
                      {flipped && prev && (
                        <span className="text-[10px] text-[#9B9B9B] line-through">{prev.action}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-right font-['JetBrains_Mono'] tabular-nums">
                    <span className="text-[#0F0F0F]">
                      {d.utility >= 0 ? "+" : ""}{d.utility.toFixed(2)}
                    </span>
                    {prev && (
                      <span className="inline-flex items-center ml-1.5">
                        {utilityDelta > 0.01 ? (
                          <TrendingUp size={11} className="text-[#16653A]" />
                        ) : utilityDelta < -0.01 ? (
                          <TrendingDown size={11} className="text-[#8B1A1A]" />
                        ) : (
                          <Minus size={11} className="text-[#9B9B9B]" />
                        )}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-[#6B6B6B]">
                    {prev && prev.new_state !== d.new_state ? (
                      <span>{prev.new_state} <span className="text-[#9B9B9B]">{"→"}</span> {d.new_state}</span>
                    ) : (
                      <span>{d.new_state || "—"}</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-[#6B6B6B] max-w-[200px] truncate">
                    {d.reasoning_chain[0]?.reasoning || d.statement || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
