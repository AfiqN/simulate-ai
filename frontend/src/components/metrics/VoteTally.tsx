import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LabelList } from "recharts";
import { Card } from "@/components/ui/card";
import type { RoundSummary, AgentDecision } from "../../types";

interface Props {
  rounds: RoundSummary[];
  agentsByRound?: Record<number, AgentDecision[]>;
}

const ACTION_COLORS = ["#16653A", "#8B1A1A", "#6B5C1A", "#2563EB", "#6B6B6B", "#9B9B9B"];

export function VoteTally({ rounds, agentsByRound }: Props) {
  const [selected, setSelected] = useState<{ round: number; action: string } | null>(null);

  if (rounds.length === 0) return null;

  const allActions = new Set<string>();
  rounds.forEach((r) => {
    Object.keys(r.vote_tally).forEach((a) => allActions.add(a));
  });
  const actions = Array.from(allActions);

  const data = rounds.map((r) => {
    const entry: Record<string, any> = { name: `R${r.round}`, round: r.round };
    actions.forEach((a) => {
      entry[a] = r.vote_tally[a] || 0;
    });
    return entry;
  });

  const handleBarClick = (entry: any, action: string) => {
    const roundNum = entry.round;
    if (selected?.round === roundNum && selected?.action === action) {
      setSelected(null);
    } else {
      setSelected({ round: roundNum, action });
    }
  };

  // Get voters for selected action+round
  const getVoters = () => {
    if (!selected || !agentsByRound) return null;
    const agents = agentsByRound[selected.round];
    if (!agents) return null;

    const voters = agents.filter((a) => a.action === selected.action);

    // Check if agent flipped from previous round
    const prevRound = agentsByRound[selected.round - 1];
    return voters.map((v) => {
      const prev = prevRound?.find((p) => p.id === v.id || p.archetype === v.archetype);
      const flipped = prev && prev.action !== v.action;
      return {
        name: v.archetype,
        previousAction: prev?.action,
        flipped,
        utility: v.utility,
      };
    });
  };

  const voters = getVoters();

  return (
    <Card className="p-4">
      <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-1">Vote Distribution</h3>
      <p className="text-[11px] text-[#B0B0B0] mb-3">Click a segment to see who voted</p>
      <ResponsiveContainer width="100%" height={rounds.length * 52 + 20}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 40, top: 0, bottom: 0 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: "#6B6B6B", fontFamily: "JetBrains Mono" }}
            width={30}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              border: "1px solid #E5E5E5",
              borderRadius: 6,
              boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
            }}
          />
          {actions.map((action, i) => (
            <Bar
              key={action}
              dataKey={action}
              stackId="votes"
              fill={ACTION_COLORS[i % ACTION_COLORS.length]}
              radius={i === actions.length - 1 ? [0, 4, 4, 0] : undefined}
              barSize={24}
              cursor="pointer"
              onClick={(entry: any) => handleBarClick(entry, action)}
            >
              <LabelList
                dataKey={action}
                position="center"
                fill="#FFFFFF"
                fontSize={11}
                fontFamily="JetBrains Mono"
                formatter={(value: number) => value > 0 ? value : ""}
              />
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3 pt-3 border-t border-[#E5E5E5]">
        {actions.map((action, i) => (
          <div key={action} className="flex items-center gap-1.5">
            <div
              className="w-2.5 h-2.5 rounded-[2px]"
              style={{ backgroundColor: ACTION_COLORS[i % ACTION_COLORS.length] }}
            />
            <span className="text-[11px] text-[#6B6B6B]">{action}</span>
          </div>
        ))}
      </div>

      {/* Voter detail panel */}
      {selected && voters && voters.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[#E5E5E5] animate-fade-in">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-[#8B8B8B] font-medium uppercase tracking-wider">
              {selected.action} voters — Round {selected.round}
            </span>
            <button onClick={() => setSelected(null)} className="text-[11px] text-[#B0B0B0] hover:text-[#0F0F0F]">
              Close
            </button>
          </div>
          <div className="space-y-1.5">
            {voters.map((voter) => (
              <div key={voter.name} className="flex items-center gap-2">
                <span className="text-[12px] text-[#0F0F0F] w-[180px] truncate">{voter.name.replace(/_/g, " ")}</span>
                <span className="text-[11px] font-['JetBrains_Mono'] text-[#6B6B6B] tabular-nums">
                  {voter.utility >= 0 ? "+" : ""}{voter.utility.toFixed(2)}
                </span>
                {voter.flipped && (
                  <span className="text-[10px] px-1.5 py-0.5 bg-[#FFF7ED] text-[#9A3412] rounded">
                    flipped from {voter.previousAction}
                  </span>
                )}
                {!voter.flipped && voter.previousAction && (
                  <span className="text-[10px] text-[#B0B0B0]">held</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
