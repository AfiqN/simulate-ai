import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import type { AgentDecision, RoundSummary } from "../../types";

interface Props {
  rounds: RoundSummary[];
  agentsByRound: Record<number, AgentDecision[]>;
}

export function RoundTimeline({ rounds: _rounds, agentsByRound }: Props) {
  const availableRounds = Object.keys(agentsByRound).map(Number).sort();

  if (availableRounds.length === 0) return null;

  return (
    <Card className="overflow-hidden">
      <Tabs defaultValue={String(availableRounds[0] || 1)}>
        <TabsList className="w-full justify-start rounded-none border-b border-[#E5E5E5] bg-transparent h-auto p-0">
          {availableRounds.map((round) => (
            <TabsTrigger
              key={round}
              value={String(round)}
              className="rounded-none border-b-2 border-transparent px-4 py-2.5 text-[13px] font-medium data-[state=active]:border-[#1A1A1A] data-[state=active]:text-[#0F0F0F] data-[state=active]:shadow-none text-[#9B9B9B]"
            >
              R{round}
            </TabsTrigger>
          ))}
        </TabsList>

        {availableRounds.map((round) => {
          const currentDecisions = agentsByRound[round] || [];
          const prevDecisions = round > 1 ? (agentsByRound[round - 1] || []) : [];
          const prevByAgent: Record<string, AgentDecision> = {};
          prevDecisions.forEach((d) => { prevByAgent[d.id] = d; });

          return (
            <TabsContent key={round} value={String(round)} className="mt-0">
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
                              <Badge variant={flipped ? "shift" : "secondary"}>
                                {d.action}
                              </Badge>
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
                              <span>{prev.new_state} <span className="text-[#9B9B9B]">→</span> {d.new_state}</span>
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
            </TabsContent>
          );
        })}
      </Tabs>
    </Card>
  );
}
