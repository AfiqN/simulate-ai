import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { FactionUpdate } from "@/types";

interface Props {
  factionUpdates: FactionUpdate[];
}

function cohesionColor(value: number): string {
  if (value >= 0.8) return "#16653A";
  if (value >= 0.5) return "#6B5C1A";
  return "#8B1A1A";
}

function cohesionBg(value: number): string {
  if (value >= 0.8) return "#ECFDF5";
  if (value >= 0.5) return "#FFFBEB";
  return "#FEF2F2";
}

export function CohesionMeter({ factionUpdates }: Props) {
  if (!factionUpdates || factionUpdates.length === 0) return null;

  const latest = factionUpdates[factionUpdates.length - 1];
  const previous = factionUpdates.length > 1 ? factionUpdates[factionUpdates.length - 2] : null;

  const factions = Object.entries(latest.factions).sort((a, b) => b[1].size - a[1].size);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Faction Cohesion</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {factions.map(([action, snapshot]) => {
            const prevCohesion = previous?.factions[action]?.cohesion;
            const delta = prevCohesion !== undefined ? snapshot.cohesion - prevCohesion : null;

            return (
              <div key={action} className="space-y-1">
                <div className="flex items-center justify-between text-[12px]">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[#0F0F0F]">{action}</span>
                    <span className="text-[#9B9B9B]">{snapshot.size} agents</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-mono text-[12px]">
                    <span style={{ color: cohesionColor(snapshot.cohesion) }}>
                      {Math.round(snapshot.cohesion * 100)}%
                    </span>
                    {delta !== null && delta !== 0 && (
                      <span className={delta > 0 ? "text-[#16653A]" : "text-[#8B1A1A]"}>
                        {delta > 0 ? "↑" : "↓"}
                        {Math.abs(Math.round(delta * 100))}
                      </span>
                    )}
                  </div>
                </div>
                {/* Bar */}
                <div
                  className="h-2 rounded-full overflow-hidden"
                  style={{ backgroundColor: cohesionBg(snapshot.cohesion) }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-500 ease-out"
                    style={{
                      width: `${Math.round(snapshot.cohesion * 100)}%`,
                      backgroundColor: cohesionColor(snapshot.cohesion),
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
        {latest.round && (
          <p className="text-[11px] text-[#9B9B9B] mt-3">Round {latest.round}</p>
        )}
      </CardContent>
    </Card>
  );
}
