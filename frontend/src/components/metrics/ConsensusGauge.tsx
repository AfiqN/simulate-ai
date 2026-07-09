import { Card } from "@/components/ui/card";

interface Props {
  rounds: { round: number; hhi: number }[];
}

function getLabel(hhi: number): { text: string; color: string } {
  if (hhi >= 0.7) return { text: "Aligned", color: "#16653A" };
  if (hhi >= 0.4) return { text: "Converging", color: "#6B5C1A" };
  return { text: "Fragmented", color: "#8B1A1A" };
}

export function ConsensusGauge({ rounds }: Props) {
  if (rounds.length === 0) return null;

  const latest = rounds[rounds.length - 1];
  const label = getLabel(latest.hhi);

  return (
    <Card className="p-4">
      <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">Consensus (HHI)</h3>
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-[28px] font-['JetBrains_Mono'] font-medium tabular-nums" style={{ color: label.color }}>
          {latest.hhi.toFixed(2)}
        </span>
        <span className="text-[13px] font-medium" style={{ color: label.color }}>
          {label.text}
        </span>
      </div>
      {rounds.length > 1 && (
        <div className="flex items-center gap-2">
          {rounds.map((r, i) => {
            const rLabel = getLabel(r.hhi);
            return (
              <div key={r.round} className="flex items-center gap-2">
                <div className="text-center">
                  <span className="block text-[15px] font-['JetBrains_Mono'] tabular-nums" style={{ color: rLabel.color }}>
                    {r.hhi.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-[#9B9B9B]">R{r.round}</span>
                </div>
                {i < rounds.length - 1 && (
                  <span className="text-[#9B9B9B] text-[12px]">→</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
