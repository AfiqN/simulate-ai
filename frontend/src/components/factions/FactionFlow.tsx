import { useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { AgentDecision, RoundSummary } from "@/types";

const FACTION_COLORS: Record<string, string> = {};
const COLOR_POOL = [
  "#16653A", "#8B1A1A", "#2563EB", "#6B5C1A", "#7C3AED",
  "#0891B2", "#BE185D", "#6B6B6B",
];

function getColor(action: string): string {
  if (!FACTION_COLORS[action]) {
    FACTION_COLORS[action] = COLOR_POOL[Object.keys(FACTION_COLORS).length % COLOR_POOL.length];
  }
  return FACTION_COLORS[action];
}

interface Props {
  agentsByRound: Record<number, AgentDecision[]>;
  rounds: RoundSummary[];
}

interface AgentPath {
  id: string;
  archetype: string;
  actions: string[];
}

interface FactionBlock {
  action: string;
  y: number;
  height: number;
  agents: string[];
}

export function FactionFlow({ agentsByRound, rounds }: Props) {
  const roundNumbers = rounds.map((r) => r.round).sort((a, b) => a - b);

  const { paths, columns } = useMemo(() => {
    if (roundNumbers.length < 2) return { paths: [], columns: [] };

    // Build agent paths across rounds
    const agentMap = new Map<string, AgentPath>();
    for (const rn of roundNumbers) {
      const decisions = agentsByRound[rn] || [];
      for (const d of decisions) {
        if (!agentMap.has(d.id)) {
          agentMap.set(d.id, { id: d.id, archetype: d.archetype, actions: [] });
        }
        agentMap.get(d.id)!.actions.push(d.action);
      }
    }

    const allPaths = Array.from(agentMap.values()).filter(
      (p) => p.actions.length === roundNumbers.length
    );

    // Build faction blocks per column
    const cols: FactionBlock[][] = [];
    for (let colIdx = 0; colIdx < roundNumbers.length; colIdx++) {
      const groups: Record<string, string[]> = {};
      for (const p of allPaths) {
        const action = p.actions[colIdx];
        if (!groups[action]) groups[action] = [];
        groups[action].push(p.id);
      }
      const sorted = Object.entries(groups).sort((a, b) => b[1].length - a[1].length);
      const blocks: FactionBlock[] = [];
      let y = 0;
      for (const [action, agents] of sorted) {
        const height = agents.length;
        blocks.push({ action, y, height, agents });
        y += height + 0.5; // gap between blocks
      }
      cols.push(blocks);
    }

    return { paths: allPaths, columns: cols };
  }, [agentsByRound, roundNumbers]);

  if (roundNumbers.length < 2 || paths.length === 0) return null;

  const totalAgents = paths.length;
  const svgWidth = 700;
  const svgHeight = 240;
  const padding = { top: 24, bottom: 24, left: 60, right: 60 };
  const chartWidth = svgWidth - padding.left - padding.right;
  const chartHeight = svgHeight - padding.top - padding.bottom;
  const colWidth = chartWidth / (roundNumbers.length - 1);
  const maxY = Math.max(...columns.map((col) => col.reduce((s, b) => s + b.height + 0.5, 0)));
  const scale = chartHeight / (maxY || 1);

  // Compute flow paths (cubic bezier between columns)
  const flows: { from: FactionBlock; to: FactionBlock; colIdx: number; count: number; color: string }[] = [];
  for (let colIdx = 0; colIdx < columns.length - 1; colIdx++) {
    const fromCol = columns[colIdx];
    const toCol = columns[colIdx + 1];
    for (const fromBlock of fromCol) {
      for (const toBlock of toCol) {
        const shared = fromBlock.agents.filter((a) => toBlock.agents.includes(a));
        if (shared.length > 0) {
          flows.push({
            from: fromBlock,
            to: toBlock,
            colIdx,
            count: shared.length,
            color: fromBlock.action === toBlock.action ? getColor(fromBlock.action) : "#D0D0D0",
          });
        }
      }
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Coalition Flow</CardTitle>
      </CardHeader>
      <CardContent>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-auto" aria-label="Faction flow diagram">
          {/* Column labels */}
          {roundNumbers.map((rn, i) => (
            <text
              key={rn}
              x={padding.left + i * colWidth}
              y={14}
              textAnchor="middle"
              className="text-[11px] fill-[#9B9B9B]"
              style={{ fontSize: 11 }}
            >
              Round {rn}
            </text>
          ))}

          {/* Faction blocks */}
          {columns.map((col, colIdx) =>
            col.map((block) => (
              <g key={`${colIdx}-${block.action}`}>
                <rect
                  x={padding.left + colIdx * colWidth - 18}
                  y={padding.top + block.y * scale}
                  width={36}
                  height={Math.max(block.height * scale - 2, 4)}
                  rx={4}
                  fill={getColor(block.action)}
                  opacity={0.85}
                />
                <text
                  x={padding.left + colIdx * colWidth}
                  y={padding.top + block.y * scale + (block.height * scale) / 2 + 3}
                  textAnchor="middle"
                  className="fill-white font-medium"
                  style={{ fontSize: 9 }}
                >
                  {block.height}
                </text>
              </g>
            ))
          )}

          {/* Flow paths */}
          {flows.map((flow, i) => {
            const x1 = padding.left + flow.colIdx * colWidth + 18;
            const x2 = padding.left + (flow.colIdx + 1) * colWidth - 18;
            const fromMidY = padding.top + (flow.from.y + flow.from.height / 2) * scale;
            const toMidY = padding.top + (flow.to.y + flow.to.height / 2) * scale;
            const thickness = Math.max((flow.count / totalAgents) * chartHeight * 0.5, 2);
            const cpOffset = (x2 - x1) * 0.4;

            return (
              <path
                key={i}
                d={`M ${x1} ${fromMidY} C ${x1 + cpOffset} ${fromMidY}, ${x2 - cpOffset} ${toMidY}, ${x2} ${toMidY}`}
                fill="none"
                stroke={flow.color}
                strokeWidth={thickness}
                opacity={0.4}
                strokeLinecap="round"
              />
            );
          })}

          {/* Legend */}
          {Array.from(new Set(columns.flat().map((b) => b.action))).map((action, i) => (
            <g key={action} transform={`translate(${padding.left + i * 90}, ${svgHeight - 8})`}>
              <circle r={4} cx={4} cy={-2} fill={getColor(action)} />
              <text x={12} y={0} style={{ fontSize: 10, fill: "#6B6B6B" }}>{action}</text>
            </g>
          ))}
        </svg>
      </CardContent>
    </Card>
  );
}
