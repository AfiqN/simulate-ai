import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { compareRuns } from "../../lib/api";
import type { RunSummaryItem, ComparisonResult } from "../../types";

interface Props {
  runs: RunSummaryItem[];
}

function DeltaBadge({ value, invert = false }: { value: number; invert?: boolean }) {
  const isPositive = invert ? value < 0 : value > 0;
  const isNegative = invert ? value > 0 : value < 0;
  const color = isPositive ? "#166534" : isNegative ? "#8B1A1A" : "#9B9B9B";
  const prefix = value > 0 ? "+" : "";
  return (
    <span className="font-['JetBrains_Mono'] text-[12px]" style={{ color }}>
      {prefix}{typeof value === "number" ? value.toFixed(3) : value}
    </span>
  );
}

export function ComparisonView({ runs }: Props) {
  const [runA, setRunA] = useState<string>("");
  const [runB, setRunB] = useState<string>("");
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const completedRuns = runs.filter((r) => r.status === "completed");

  const handleCompare = async () => {
    if (!runA || !runB || runA === runB) return;
    setLoading(true);
    setError(null);
    try {
      const data = await compareRuns(runA, runB);
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="p-4">
          <h3 className="text-[13px] font-medium tracking-[-0.02em] mb-3">Compare Runs</h3>
          <div className="flex items-end gap-3">
            <div className="flex-1 space-y-1">
              <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
                Run A
              </label>
              <Select value={runA} onChange={(e) => setRunA(e.target.value)} className="w-full">
                <option value="">Select run...</option>
                {completedRuns.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.scenario_name.slice(0, 40)} ({r.verdict || "—"})
                  </option>
                ))}
              </Select>
            </div>
            <span className="text-[#9B9B9B] text-[14px] pb-1.5">vs</span>
            <div className="flex-1 space-y-1">
              <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
                Run B
              </label>
              <Select value={runB} onChange={(e) => setRunB(e.target.value)} className="w-full">
                <option value="">Select run...</option>
                {completedRuns.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.scenario_name.slice(0, 40)} ({r.verdict || "—"})
                  </option>
                ))}
              </Select>
            </div>
            <Button
              onClick={handleCompare}
              disabled={loading || !runA || !runB || runA === runB}
              size="default"
            >
              {loading ? "Comparing..." : "Compare"}
            </Button>
          </div>
          {error && <p className="text-[13px] text-[#8B1A1A] mt-2">{error}</p>}
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardContent className="p-4 space-y-4">
            {/* Verdict comparison */}
            <div>
              <h4 className="text-[12px] text-[#9B9B9B] uppercase tracking-wider font-medium mb-2">
                Verdict
              </h4>
              <div className="flex items-center gap-3">
                <span className="text-[14px] font-medium">{result.verdict.run_a}</span>
                <span className="text-[#9B9B9B]">→</span>
                <span className="text-[14px] font-medium">{result.verdict.run_b}</span>
                {result.verdict.changed && (
                  <span className="text-[11px] px-2 py-0.5 bg-[#FEF3CD] text-[#6B5C1A] rounded">
                    Changed
                  </span>
                )}
              </div>
            </div>

            {/* Stability metrics */}
            <div>
              <h4 className="text-[12px] text-[#9B9B9B] uppercase tracking-wider font-medium mb-2">
                Stability Metrics
              </h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#FAFAFA] rounded p-3">
                  <div className="text-[11px] text-[#9B9B9B]">Decision Stability</div>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="font-['JetBrains_Mono'] text-[14px]">
                      {result.stability.decision_stability.run_a.toFixed(3)}
                    </span>
                    <span className="text-[#9B9B9B]">→</span>
                    <span className="font-['JetBrains_Mono'] text-[14px]">
                      {result.stability.decision_stability.run_b.toFixed(3)}
                    </span>
                    <DeltaBadge value={result.stability.decision_stability.delta} />
                  </div>
                </div>
                <div className="bg-[#FAFAFA] rounded p-3">
                  <div className="text-[11px] text-[#9B9B9B]">Utility Drift (mean)</div>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="font-['JetBrains_Mono'] text-[14px]">
                      {result.stability.utility_drift_mean.run_a.toFixed(3)}
                    </span>
                    <span className="text-[#9B9B9B]">→</span>
                    <span className="font-['JetBrains_Mono'] text-[14px]">
                      {result.stability.utility_drift_mean.run_b.toFixed(3)}
                    </span>
                    <DeltaBadge value={result.stability.utility_drift_mean.delta} invert />
                  </div>
                </div>
              </div>
            </div>

            {/* Vote tally diff */}
            {Object.keys(result.vote_tally).length > 0 && (
              <div>
                <h4 className="text-[12px] text-[#9B9B9B] uppercase tracking-wider font-medium mb-2">
                  Vote Tally Diff
                </h4>
                <div className="space-y-2">
                  {Object.entries(result.vote_tally).map(([round, actions]) => (
                    <div key={round} className="bg-[#FAFAFA] rounded p-3">
                      <div className="text-[11px] text-[#9B9B9B] mb-1 uppercase">{round}</div>
                      <div className="flex flex-wrap gap-3">
                        {Object.entries(actions).map(([action, counts]) => (
                          <div key={action} className="text-[13px]">
                            <span className="font-medium">{action}:</span>{" "}
                            <span className="font-['JetBrains_Mono']">{counts.run_a}</span>
                            <span className="text-[#9B9B9B] mx-1">→</span>
                            <span className="font-['JetBrains_Mono']">{counts.run_b}</span>
                            {counts.delta !== 0 && (
                              <span className="ml-1">
                                <DeltaBadge value={counts.delta} />
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timing */}
            <div className="flex items-center gap-3 text-[13px] text-[#9B9B9B] pt-2 border-t border-[#E5E5E5]">
              <span>Time: {result.timings.run_a_total.toFixed(1)}s → {result.timings.run_b_total.toFixed(1)}s</span>
              <DeltaBadge value={result.timings.delta} invert />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
