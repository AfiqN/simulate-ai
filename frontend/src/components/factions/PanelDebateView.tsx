import { useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import type { AgentDecision, RoundSummary } from "@/types";

interface Props {
  agentsByRound: Record<number, AgentDecision[]>;
  rounds: RoundSummary[];
}

interface ChallengeEdge {
  challenger: string;
  challengerAction: string;
  target: string;
  targetAction: string;
}

const ACTION_COLORS: Record<string, string> = {};
const PALETTE = ["#16653A", "#8B1A1A", "#2563EB", "#6B5C1A", "#7C3AED", "#0891B2"];

function getActionColor(action: string): string {
  if (!ACTION_COLORS[action]) {
    ACTION_COLORS[action] = PALETTE[Object.keys(ACTION_COLORS).length % PALETTE.length];
  }
  return ACTION_COLORS[action];
}

export function PanelDebateView({ agentsByRound, rounds }: Props) {
  const roundNumbers = rounds.map((r) => r.round).filter((r) => r >= 2).sort((a, b) => a - b);

  const edgesByRound = useMemo(() => {
    const result: Record<number, ChallengeEdge[]> = {};

    for (const rn of roundNumbers) {
      if (rn < 2) continue;
      const prevRound = rn - 1;
      const prevDecisions = agentsByRound[prevRound] || [];
      const currDecisions = agentsByRound[rn] || [];

      if (prevDecisions.length === 0 || currDecisions.length === 0) continue;

      // Determine majority/minority from previous round
      const actionCounts: Record<string, number> = {};
      for (const d of prevDecisions) {
        actionCounts[d.action] = (actionCounts[d.action] || 0) + 1;
      }
      const sorted = Object.entries(actionCounts).sort((a, b) => b[1] - a[1]);
      if (sorted.length < 2) continue;

      const majorityAction = sorted[0][0];
      const majorityAgents = prevDecisions.filter((d) => d.action === majorityAction);
      const minorityAgents = prevDecisions.filter((d) => d.action !== majorityAction);

      // Each majority agent is "challenged" by the strongest minority agent(s)
      const edges: ChallengeEdge[] = [];
      const challengersPerTarget = Math.min(2, minorityAgents.length);
      const topMinority = minorityAgents
        .sort((a, b) => Math.abs(b.utility) - Math.abs(a.utility))
        .slice(0, challengersPerTarget);

      for (const target of majorityAgents) {
        for (const challenger of topMinority) {
          edges.push({
            challenger: challenger.archetype,
            challengerAction: challenger.action,
            target: target.archetype,
            targetAction: target.action,
          });
        }
      }

      result[rn] = edges;
    }

    return result;
  }, [agentsByRound, roundNumbers]);

  if (roundNumbers.length === 0) return null;

  // Check if there's any meaningful panel data
  const hasData = Object.values(edgesByRound).some((e) => e.length > 0);
  if (!hasData) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Panel Debate Challenges</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue={String(roundNumbers[0])}>
          <TabsList>
            {roundNumbers.map((rn) => (
              <TabsTrigger key={rn} value={String(rn)}>
                Round {rn}
              </TabsTrigger>
            ))}
          </TabsList>

          {roundNumbers.map((rn) => {
            const edges = edgesByRound[rn] || [];
            // Group edges by target
            const byTarget: Record<string, ChallengeEdge[]> = {};
            for (const e of edges) {
              if (!byTarget[e.target]) byTarget[e.target] = [];
              byTarget[e.target].push(e);
            }

            return (
              <TabsContent key={rn} value={String(rn)}>
                {edges.length === 0 ? (
                  <p className="text-[12px] text-[#9B9B9B] py-4">No panel challenges this round.</p>
                ) : (
                  <div className="space-y-2 mt-2">
                    {Object.entries(byTarget).map(([target, challengers]) => (
                      <div
                        key={target}
                        className="flex items-center gap-2 py-2 px-3 rounded-md border border-[#F0F0F0] bg-[#FAFAFA]"
                      >
                        {/* Challengers */}
                        <div className="flex flex-col gap-0.5">
                          {challengers.map((c, i) => (
                            <span
                              key={i}
                              className="text-[11px] font-medium px-1.5 py-0.5 rounded"
                              style={{
                                color: getActionColor(c.challengerAction),
                                backgroundColor: getActionColor(c.challengerAction) + "15",
                              }}
                            >
                              {c.challenger}
                            </span>
                          ))}
                        </div>

                        {/* Arrow */}
                        <svg width="24" height="12" viewBox="0 0 24 12" fill="none" className="shrink-0">
                          <path
                            d="M2 6h18m0 0l-3.5-3.5M20 6l-3.5 3.5"
                            stroke="#9B9B9B"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>

                        {/* Target */}
                        <span
                          className="text-[12px] font-semibold px-2 py-0.5 rounded"
                          style={{
                            color: getActionColor(challengers[0].targetAction),
                            backgroundColor: getActionColor(challengers[0].targetAction) + "15",
                          }}
                        >
                          {target}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </TabsContent>
            );
          })}
        </Tabs>
      </CardContent>
    </Card>
  );
}
