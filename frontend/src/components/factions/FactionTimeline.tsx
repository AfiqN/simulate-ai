import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

const FACTION_COLORS = [
  "#16653A", "#8B1A1A", "#2563EB", "#6B5C1A", "#7C3AED",
  "#0891B2", "#BE185D", "#6B6B6B",
];

interface Props {
  history: { round: number; factions: Record<string, number> }[];
}

export function FactionTimeline({ history }: Props) {
  if (!history || history.length === 0) return null;

  // Collect all unique faction actions
  const allActions = Array.from(
    new Set(history.flatMap((h) => Object.keys(h.factions)))
  ).sort();

  // Transform to Recharts data format
  const data = history.map((h) => {
    const entry: Record<string, string | number> = { round: `R${h.round}` };
    for (const action of allActions) {
      entry[action] = h.factions[action] ?? 0;
    }
    return entry;
  });

  const colorMap: Record<string, string> = {};
  allActions.forEach((action, i) => {
    colorMap[action] = FACTION_COLORS[i % FACTION_COLORS.length];
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Faction Size Over Rounds</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 12, left: -8, bottom: 0 }}>
              <XAxis
                dataKey="round"
                tick={{ fontSize: 11, fill: "#9B9B9B" }}
                axisLine={{ stroke: "#E5E5E5" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#9B9B9B" }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  border: "1px solid #E5E5E5",
                  borderRadius: 6,
                  boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                iconType="circle"
                iconSize={8}
              />
              {allActions.map((action) => (
                <Area
                  key={action}
                  type="monotone"
                  dataKey={action}
                  stackId="1"
                  stroke={colorMap[action]}
                  fill={colorMap[action]}
                  fillOpacity={0.6}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
