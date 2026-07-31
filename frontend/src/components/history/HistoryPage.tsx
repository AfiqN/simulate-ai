import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, Trash2 } from "lucide-react";
import { getHistory, removeFromHistory, clearAllHistory, type HistoryEntry } from "../../lib/history";

function formatTimeAgo(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  return new Date(timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const v = verdict.toLowerCase();
  const style = v.includes("resilient")
    ? "bg-[#ECFDF5] text-[#065F46]"
    : v.includes("fragile")
    ? "bg-[#FEF2F2] text-[#991B1B]"
    : "bg-[#F3F0FF] text-[#5B21B6]";
  return (
    <span className={`px-2 py-0.5 text-[11px] font-medium rounded-[4px] ${style}`}>
      {verdict}
    </span>
  );
}

interface Props {
  onBack: () => void;
}

export function HistoryPage({ onBack }: Props) {
  const [entries, setEntries] = useState<HistoryEntry[]>(getHistory());
  const navigate = useNavigate();

  const handleRemove = (e: React.MouseEvent, runId: string) => {
    e.stopPropagation();
    removeFromHistory(runId);
    setEntries(getHistory());
  };

  const handleClearAll = () => {
    clearAllHistory();
    setEntries([]);
  };

  return (
    <div className="py-8 sm:py-12">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <button
            onClick={onBack}
            className="text-[13px] text-[#8B8B8B] hover:text-[#0F0F0F] transition-colors mb-2 block"
          >
            ← Back
          </button>
          <h1 className="text-[24px] sm:text-[32px] font-semibold tracking-[-0.03em] text-[#0F0F0F]">
            History
          </h1>
          <p className="text-[14px] text-[#6B6B6B] mt-1">
            Your past simulations — stored locally in this browser.
          </p>
        </div>
        {entries.length > 0 && (
          <button
            onClick={handleClearAll}
            className="px-3 py-1.5 text-[12px] text-[#8B8B8B] hover:text-[#8B1A1A] border border-[#E5E5E5] hover:border-[#8B1A1A]/30 rounded-[6px] transition-colors"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Empty state */}
      {entries.length === 0 && (
        <div className="text-center py-16 border border-[#E5E5E5] rounded-[12px]">
          <Clock size={24} className="mx-auto text-[#D0D0D0] mb-3" />
          <p className="text-[14px] text-[#8B8B8B]">No simulations yet.</p>
          <p className="text-[13px] text-[#B0B0B0] mt-1">Run a simulation and it will appear here.</p>
          <button
            onClick={() => navigate("/simulate")}
            className="mt-4 px-5 py-2 text-[13px] font-medium bg-[#0F0F0F] text-white rounded-[8px] hover:bg-[#2A2A2A] transition-colors"
          >
            Run a simulation
          </button>
        </div>
      )}

      {/* History list */}
      {entries.length > 0 && (
        <div className="space-y-2">
          {entries.map((entry) => (
            <button
              key={entry.runId}
              onClick={() => navigate(`/run/${entry.runId}`)}
              className="group w-full text-left flex items-center gap-4 p-4 border border-[#E5E5E5] rounded-[10px] hover:border-[#0F0F0F]/20 hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-all duration-150"
            >
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-medium text-[#0F0F0F] truncate">
                  {entry.scenarioName}
                </p>
                <div className="flex items-center gap-2 mt-1 text-[12px] text-[#8B8B8B] font-['JetBrains_Mono']">
                  <span>{entry.agents}a · {entry.depth}</span>
                  {entry.duration && <span>· {Math.round(entry.duration)}s</span>}
                  <span>· {formatTimeAgo(entry.timestamp)}</span>
                </div>
              </div>
              <VerdictBadge verdict={entry.verdict} />
              <button
                onClick={(e) => handleRemove(e, entry.runId)}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-[4px] hover:bg-[#FEF2F2] transition-all"
              >
                <Trash2 size={14} className="text-[#B0B0B0] hover:text-[#8B1A1A]" />
              </button>
            </button>
          ))}
        </div>
      )}

      {/* Footer note */}
      {entries.length > 0 && (
        <p className="text-[11px] text-[#B0B0B0] mt-6 text-center">
          History is stored locally in your browser. Clearing browser data will remove it.
        </p>
      )}
    </div>
  );
}
