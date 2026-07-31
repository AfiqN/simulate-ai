import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LabelList } from "recharts";
import { Card } from "@/components/ui/card";
import type { AgentDecision } from "../../types";

interface DimensionStats {
  [round: string]: {
    [dimension: string]: { mean: number; stdev: number; min: number; max: number };
  };
}

interface Props {
  stats: DimensionStats;
  agentsByRound?: Record<number, AgentDecision[]>;
}

const ROUND_COLORS: Record<string, string> = {
  r1: "#6B6B6B",
  r2: "#2563EB",
  r3: "#8B1A1A",
  r4: "#16653A",
};

export function DimensionChart({ stats, agentsByRound }: Props) {
  const [selected, setSelected] = useState<{ dimension: string; round: string } | null>(null);

  if (!stats || Object.keys(stats).length === 0) return null;

  // stats format: { r1: { dim: { mean, stdev, min, max } }, r2: {...} }
  const roundKeys = Object.keys(stats).sort();
  const dimensions = new Set<string>();
  roundKeys.forEach((r) => {
    Object.keys(stats[r]).forEach((d) => dimensions.add(d));
  });
  const dimList = Array.from(dimensions);

  const data = dimList.map((dim) => {
    const entry: Record<string, any> = {
      dimension: dim.length > 16 ? dim.slice(0, 16) + "…" : dim,
      fullName: dim,
    };
    roundKeys.forEach((r) => {
      entry[r] = stats[r]?.[dim]?.mean ?? 0;
    });
    return entry;
  });

  const handleBarClick = (dimEntry: any, roundKey: string) => {
    const fullName = dimEntry.fullName;
    if (selected?.dimension === fullName && selected?.round === roundKey) {
      setSelected(null);
    } else {
      setSelected({ dimension: fullName, round: roundKey });
    }
  };

  // Get agent scores for selected dimension+round
  const getAgentBreakdown = () => {
    if (!selected || !agentsByRound) return null;
    const roundNum = parseInt(selected.round.replace("r", ""));
    const agents = agentsByRound[roundNum];
    if (!agents) return null;

    return agents
      .filter((a) => a.utility_dimensions && selected.dimension in a.utility_dimensions)
      .map((a) => ({
        name: a.archetype,
        score: a.utility_dimensions[selected.dimension],
      }))
      .sort((a, b) => a.score - b.score);
  };

  const breakdown = getAgentBreakdown();

  return (
    <Card className="p-4">
      <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">Dimension Means by Round</h3>
      <p className="text-[11px] text-[#B0B0B0] mb-3">Click a bar to see per-agent breakdown</p>
      <ResponsiveContainer width="100%" height={Math.max(220, dimList.length * 28)}>
        <BarChart data={data} margin={{ left: 0, right: 20, top: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E5" vertical={false} />
          <XAxis
            dataKey="dimension"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: "#6B6B6B" }}
            interval={0}
            angle={dimList.length > 4 ? -20 : 0}
            textAnchor={dimList.length > 4 ? "end" : "middle"}
            height={dimList.length > 4 ? 50 : 30}
          />
          <YAxis
            domain={[-1, 1]}
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: "#9B9B9B", fontFamily: "JetBrains Mono" }}
            width={35}
            tickCount={5}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              border: "1px solid #E5E5E5",
              borderRadius: 6,
              boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
            }}
            formatter={(value: number, name: string) => [
              value.toFixed(3),
              name.replace("r", "R"),
            ]}
            labelFormatter={(label) => {
              const item = data.find((d) => d.dimension === label);
              return item?.fullName || label;
            }}
          />
          {roundKeys.map((r) => (
            <Bar
              key={r}
              dataKey={r}
              fill={ROUND_COLORS[r] || "#6B6B6B"}
              radius={[3, 3, 0, 0]}
              maxBarSize={24}
              cursor="pointer"
              onClick={(entry: any) => handleBarClick(entry, r)}
            >
              <LabelList
                dataKey={r}
                position="top"
                fill={ROUND_COLORS[r] || "#6B6B6B"}
                fontSize={9}
                fontFamily="JetBrains Mono"
                formatter={(value: number) => Math.abs(value) >= 0.01 ? value.toFixed(2) : ""}
              />
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 mt-2 pt-2 border-t border-[#E5E5E5]">
        {roundKeys.map((r) => (
          <div key={r} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-[2px]" style={{ backgroundColor: ROUND_COLORS[r] || "#6B6B6B" }} />
            <span className="text-[11px] text-[#6B6B6B]">{r.replace("r", "R")}</span>
          </div>
        ))}
      </div>

      {/* Agent breakdown panel */}
      {selected && breakdown && breakdown.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[#E5E5E5] animate-fade-in">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] text-[#8B8B8B] font-medium uppercase tracking-wider">
              {selected.dimension.replace(/_/g, " ")} — {selected.round.replace("r", "Round ")}
            </span>
            <button onClick={() => setSelected(null)} className="text-[11px] text-[#B0B0B0] hover:text-[#0F0F0F]">
              Close
            </button>
          </div>
          <div className="space-y-1.5">
            {breakdown.map((agent) => (
              <div key={agent.name} className="flex items-center gap-2">
                <span className="text-[12px] text-[#6B6B6B] w-[180px] truncate">{agent.name.replace(/_/g, " ")}</span>
                <div className="flex-1 h-[6px] bg-[#F0F0F0] rounded-full overflow-hidden relative">
                  <div
                    className="absolute top-0 h-full rounded-full"
                    style={{
                      backgroundColor: agent.score >= 0 ? "#16653A" : "#8B1A1A",
                      left: agent.score >= 0 ? "50%" : undefined,
                      right: agent.score < 0 ? "50%" : undefined,
                      width: `${Math.abs(agent.score) * 50}%`,
                    }}
                  />
                </div>
                <span className="text-[11px] font-['JetBrains_Mono'] text-[#6B6B6B] w-[50px] text-right tabular-nums">
                  {agent.score >= 0 ? "+" : ""}{agent.score.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
