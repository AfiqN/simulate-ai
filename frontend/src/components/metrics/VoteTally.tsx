import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { RoundSummary } from "../../types";

interface Props {
  rounds: RoundSummary[];
}

// Deterministic color assignment for actions
const ACTION_COLORS = ["#16653A", "#8B1A1A", "#6B5C1A", "#2563EB", "#6B6B6B", "#9B9B9B"];

export function VoteTally({ rounds }: Props) {
  if (rounds.length === 0) return null;

  // Collect all unique actions across rounds
  const allActions = new Set<string>();
  rounds.forEach((r) => {
    Object.keys(r.vote_tally).forEach((a) => allActions.add(a));
  });
  const actions = Array.from(allActions);

  // Build chart data
  const data = rounds.map((r) => {
    const entry: Record<string, any> = { name: `R${r.round}` };
    actions.forEach((a) => {
      entry[a] = r.vote_tally[a] || 0;
    });
    return entry;
  });

  return (
    <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
      <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">Vote Distribution</h3>
      <ResponsiveContainer width="100%" height={rounds.length * 40 + 20}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
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
              boxShadow: "none",
            }}
          />
          {actions.map((action, i) => (
            <Bar
              key={action}
              dataKey={action}
              stackId="votes"
              fill={ACTION_COLORS[i % ACTION_COLORS.length]}
              radius={i === actions.length - 1 ? [0, 4, 4, 0] : undefined}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-3">
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
    </div>
  );
}
