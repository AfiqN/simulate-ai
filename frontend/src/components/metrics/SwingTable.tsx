import { Badge } from "../common/Badge";
import type { SwingEntry } from "../../types";

interface Props {
  swings: Record<string, SwingEntry[]>;
}

export function SwingTable({ swings }: Props) {
  // Flatten all swings across rounds and sort
  const allSwings: (SwingEntry & { round: string })[] = [];
  Object.entries(swings).forEach(([round, entries]) => {
    entries.forEach((e) => allSwings.push({ ...e, round }));
  });

  if (allSwings.length === 0) {
    return (
      <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
        <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">Action Swings</h3>
        <p className="text-[13px] text-[#9B9B9B]">No action swings detected.</p>
      </div>
    );
  }

  return (
    <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
      <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">Action Swings</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-[#E5E5E5]">
              <th className="text-left pb-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">Agent</th>
              <th className="text-left pb-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">Round</th>
              <th className="text-left pb-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">From → To</th>
              <th className="text-left pb-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-normal">Driver</th>
            </tr>
          </thead>
          <tbody>
            {allSwings.map((s, i) => (
              <tr key={i} className="border-b border-[#E5E5E5] last:border-b-0">
                <td className="py-2 font-medium text-[#0F0F0F]">{s.archetype}</td>
                <td className="py-2 font-['JetBrains_Mono'] text-[#6B6B6B] text-[12px]">
                  {s.round.replace("_", " ").replace("round", "R")}
                </td>
                <td className="py-2">
                  <span className="text-[#9B9B9B]">{s.from_action}</span>
                  <span className="mx-1.5 text-[#9B9B9B]">→</span>
                  <Badge label={s.to_action} variant="shift" size="sm" />
                </td>
                <td className="py-2 text-[#6B6B6B]">{s.driver_dimension}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
