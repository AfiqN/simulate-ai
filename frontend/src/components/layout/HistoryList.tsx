import { useState, useEffect } from "react";
import { getHistory, getRunDetail } from "../../lib/api";
import type { RunSummaryItem, SimulationResult } from "../../types";

interface Props {
  onLoadResult: (result: SimulationResult) => void;
}

function getVerdictColor(verdict?: string): string {
  if (!verdict) return "#9B9B9B";
  const v = verdict.toLowerCase();
  if (v.includes("resilient")) return "#16653A";
  if (v.includes("fragile")) return "#8B1A1A";
  return "#6B5C1A";
}

export function HistoryList({ onLoadResult }: Props) {
  const [runs, setRuns] = useState<RunSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHistory()
      .then((data) => {
        setRuns(data.runs);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const handleClick = async (id: string) => {
    setLoadingId(id);
    try {
      const detail = await getRunDetail(id);
      if (detail.result) {
        onLoadResult(detail.result);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoadingId(null);
    }
  };

  if (loading) {
    return (
      <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
        <p className="text-[13px] text-[#9B9B9B]">Loading history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
        <p className="text-[13px] text-[#8B1A1A]">{error}</p>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="border border-[#E5E5E5] rounded-[6px] bg-white p-4">
        <p className="text-[13px] text-[#9B9B9B]">No simulation runs yet.</p>
      </div>
    );
  }

  return (
    <div className="border border-[#E5E5E5] rounded-[6px] bg-white divide-y divide-[#E5E5E5]">
      {runs.map((run) => (
        <button
          key={run.id}
          onClick={() => handleClick(run.id)}
          disabled={loadingId === run.id}
          className="w-full px-4 py-3 text-left hover:bg-[#FAFAFA] transition-colors disabled:opacity-50 flex items-center justify-between"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-medium text-[#0F0F0F] truncate">
                {run.scenario_name}
              </span>
              {run.verdict && (
                <span
                  className="text-[11px] font-medium"
                  style={{ color: getVerdictColor(run.verdict) }}
                >
                  {run.verdict}
                </span>
              )}
            </div>
            <div className="flex gap-3 mt-0.5 text-[12px] text-[#9B9B9B]">
              <span>{run.status}</span>
              {run.agent_count && <span>{run.agent_count} agents</span>}
              {run.elapsed_s && (
                <span className="font-['JetBrains_Mono']">{run.elapsed_s.toFixed(1)}s</span>
              )}
              <span>{new Date(run.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          {loadingId === run.id && (
            <span className="text-[12px] text-[#9B9B9B]">Loading...</span>
          )}
        </button>
      ))}
    </div>
  );
}
