import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LabelList } from "recharts";

interface DimensionStats {
  [dimension: string]: {
    [round: string]: { mean: number; stdev: number; min: number; max: number };
  };
}

interface Props {
  stats: DimensionStats;
}

const ROUND_COLORS: Record<string, string> = {
  round_1: "#6B6B6B",
  round_2: "#2563EB",
  round_3: "#8B1A1A",
  round_4: "#16653A",
};

export function DimensionChart({ stats }: Props) {
  if (!stats || Object.keys(stats).length === 0) return null;

  const dimensions = Object.keys(stats);
  const rounds = new Set<string>();
  Object.values(stats).forEach((dimData) => {
    Object.keys(dimData).forEach((r) => rounds.add(r));
  });
  const roundKeys = Array.from(rounds).sort();

  // Build chart data
  const data = dimensions.map((dim) => {
    const entry: Record<string, any> = {
      dimension: dim.length > 16 ? dim.slice(0, 16) + "…" : dim,
      fullName: dim,
    };
    roundKeys.forEach((r) => {
      entry[r] = stats[dim]?.[r]?.mean ?? 0;
    });
    return entry;
  });

  return (
    <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
      <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">Dimension Means by Round</h3>
      <ResponsiveContainer width="100%" height={Math.max(220, dimensions.length * 28)}>
        <BarChart data={data} margin={{ left: 0, right: 20, top: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E5E5" vertical={false} />
          <XAxis
            dataKey="dimension"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fill: "#6B6B6B" }}
            interval={0}
            angle={dimensions.length > 4 ? -20 : 0}
            textAnchor={dimensions.length > 4 ? "end" : "middle"}
            height={dimensions.length > 4 ? 50 : 30}
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
              name.replace("_", " ").replace("round", "R"),
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
            <span className="text-[11px] text-[#6B6B6B]">{r.replace("_", " ").replace("round", "R")}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
