import { useState, useRef, useCallback } from "react";
import { generateReport } from "../../lib/pdfReport";
import { ReportSection } from "./ReportSection";
import { RoundTimeline } from "./RoundTimeline";
import { AdversarialResultPanel } from "./AdversarialResultPanel";
import { VoteTally } from "../metrics/VoteTally";
import { ConsensusGauge } from "../metrics/ConsensusGauge";
import { DimensionChart } from "../metrics/DimensionChart";
import { SwingTable } from "../metrics/SwingTable";
import { ExportButton } from "../metrics/ExportButton";
import {
  FactionTimeline,
  FactionFlow,
  CohesionMeter,
  DefectionLog,
  PanelDebateView,
} from "../factions";
import { ConditionalTriggersPanel } from "../dynamics/ConditionalTriggersPanel";
import { HistoricalContextPanel } from "../dynamics/HistoricalContextPanel";
import type { SimulationResult, RoundSummary, AgentDecision, SchemaData, FactionUpdate, TriggersEvent, HistoricalPrecedent, AdversarialResult } from "../../types";

interface Props {
  result: SimulationResult;
  rounds: RoundSummary[];
  agentsByRound: Record<number, AgentDecision[]>;
  schema: SchemaData | null;
  factionUpdates: FactionUpdate[];
  triggersEvents?: TriggersEvent[];
  historicalPrecedents?: HistoricalPrecedent[];
  adversarialResult?: AdversarialResult | null;
  runId?: string;
  onReset: () => void;
}

function computeHHI(voteTally: Record<string, number>, totalAgents: number): number {
  if (totalAgents === 0) return 0;
  const shares = Object.values(voteTally).map((count) => count / totalAgents);
  return shares.reduce((sum, s) => sum + s * s, 0);
}

function CollapsibleSection({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-[#E5E5E5] rounded-[10px] overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-5 py-3.5 flex items-center justify-between text-left hover:bg-[#FAFAFA] transition-colors"
      >
        <span className="text-[13px] font-medium text-[#0F0F0F]">{title}</span>
        <span className={`text-[#8B8B8B] text-[12px] transition-transform duration-200 ${open ? "rotate-180" : ""}`}>
          ▾
        </span>
      </button>
      {open && (
        <div className="px-5 pb-5 border-t border-[#F0F0F0] pt-4 animate-fade-in">
          {children}
        </div>
      )}
    </div>
  );
}

function getVerdictColor(verdict: string) {
  const v = verdict.toLowerCase();
  if (v.includes("resilient")) return "text-[#16653A]";
  if (v.includes("fragile") || v.includes("rejected")) return "text-[#8B1A1A]";
  return "text-[#5B21B6]";
}

export function ResultsView({ result, rounds, agentsByRound, schema, factionUpdates, triggersEvents, historicalPrecedents, adversarialResult, runId, onReset }: Props) {
  const [exporting, setExporting] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const reportRef = useRef<HTMLDivElement>(null);

  const handleShare = useCallback(() => {
    if (!runId) return;
    const url = `${window.location.origin}?run=${runId}`;
    navigator.clipboard.writeText(url).then(() => {
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    });
  }, [runId]);

  const handleExportPdf = useCallback(async () => {
    setExporting(true);
    try {
      generateReport(result, rounds, schema);
    } catch (err) {
      console.error("PDF export failed:", err);
    } finally {
      setExporting(false);
    }
  }, [result, rounds, schema]);

  const verdict = result.resilience_metrics?.verdict || result.verdict || "Unknown";
  const stability = result.resilience_metrics?.decision_stability;
  const drift = result.resilience_metrics?.utility_drift_mean;
  const latestRound = rounds[rounds.length - 1];
  const totalAgents = latestRound?.decisions?.length || 0;

  const crisisStress = typeof result.crisis_event === "object"
    ? result.crisis_event?.stress
    : typeof result.crisis_event === "string"
    ? result.crisis_event
    : null;

  return (
    <div className="space-y-5 animate-fade-in" ref={reportRef}>
      {/* Top: Verdict card */}
      <div className="bg-[#0F0F0F] rounded-[12px] p-6 sm:p-8 text-white">
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-[11px] text-[#6B6B6B] uppercase tracking-wider font-['JetBrains_Mono'] mb-1">
              Simulation Complete
            </p>
            <h1 className="text-[18px] sm:text-[22px] font-medium tracking-[-0.02em] leading-tight">
              {schema?.scenario_name || result.scenario_name || "Simulation Report"}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {runId && (
              <button
                onClick={handleShare}
                className="px-3 py-1.5 text-[12px] text-[#8B8B8B] border border-[#3A3A3A] rounded-[6px] hover:border-[#6B6B6B] hover:text-white transition-colors"
              >
                {shareCopied ? "Copied!" : "Share"}
              </button>
            )}
            <button
              onClick={handleExportPdf}
              disabled={exporting}
              className="px-3 py-1.5 text-[12px] text-[#8B8B8B] border border-[#3A3A3A] rounded-[6px] hover:border-[#6B6B6B] hover:text-white transition-colors disabled:opacity-50"
            >
              {exporting ? "Exporting…" : "Export PDF"}
            </button>
          </div>
        </div>

        {/* Verdict + key metrics */}
        <div className="flex flex-wrap items-end gap-8">
          <div>
            <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">Verdict</p>
            <p className={`text-[28px] sm:text-[32px] font-semibold tracking-[-0.02em] ${getVerdictColor(verdict).replace("text-", "text-")} ${verdict.toLowerCase().includes("resilient") ? "text-[#4ADE80]" : verdict.toLowerCase().includes("fragile") ? "text-[#EF4444]" : "text-[#C4B5FD]"}`}>
              {verdict}
            </p>
          </div>
          {stability !== undefined && (
            <div>
              <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">Stability</p>
              <p className="text-[20px] font-['JetBrains_Mono'] font-medium text-white tabular-nums">
                {(stability * 100).toFixed(0)}%
              </p>
            </div>
          )}
          {drift !== undefined && (
            <div>
              <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">Utility Drift</p>
              <p className="text-[20px] font-['JetBrains_Mono'] font-medium text-white tabular-nums">
                {drift >= 0 ? "+" : ""}{drift.toFixed(3)}
              </p>
            </div>
          )}
          {totalAgents > 0 && (
            <div>
              <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">Agents</p>
              <p className="text-[20px] font-['JetBrains_Mono'] font-medium text-white tabular-nums">
                {totalAgents}
              </p>
            </div>
          )}
          {result.timings?.total && (
            <div>
              <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">Duration</p>
              <p className="text-[20px] font-['JetBrains_Mono'] font-medium text-white tabular-nums">
                {result.timings.total.toFixed(1)}s
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Crisis event callout */}
      {crisisStress && (
        <div className="flex items-start gap-3 p-4 bg-[#FAFAFA] border border-[#E5E5E5] rounded-[10px]">
          <span className="text-[11px] text-[#8B8B8B] uppercase tracking-wider font-medium shrink-0 mt-0.5">Crisis</span>
          <p className="text-[13px] text-[#0F0F0F] leading-relaxed">{crisisStress}</p>
        </div>
      )}

      {/* Analysis Report — the main content */}
      <div className="border border-[#E5E5E5] rounded-[10px] bg-white p-5 sm:p-8">
        <h2 className="text-[13px] text-[#8B8B8B] uppercase tracking-wider font-medium mb-4">Analysis</h2>
        <ReportSection result={result} />
      </div>

      {/* Metrics — collapsible */}
      <CollapsibleSection title="Metrics & Charts" defaultOpen={true}>
        <div className="space-y-4">
          <VoteTally rounds={rounds} />
          {result.quantitative_metrics?.dimension_stats && (
            <DimensionChart stats={result.quantitative_metrics.dimension_stats} />
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ConsensusGauge
              rounds={rounds.map((r) => ({
                round: r.round,
                hhi: r.consensus_index ?? computeHHI(r.vote_tally, r.decisions?.length || 0),
              }))}
            />
            {result.quantitative_metrics?.swing_analysis && (
              <SwingTable swings={result.quantitative_metrics.swing_analysis} />
            )}
          </div>
        </div>
      </CollapsibleSection>

      {/* Adversarial Debate */}
      {adversarialResult && adversarialResult.claims.length > 0 && (
        <CollapsibleSection title="Adversarial Debate" defaultOpen={true}>
          <AdversarialResultPanel result={adversarialResult} />
        </CollapsibleSection>
      )}

      {/* Coalition Dynamics */}
      {!adversarialResult && result.faction_metrics && (
        <CollapsibleSection title="Coalition Dynamics">
          <div className="space-y-4">
            <FactionTimeline history={result.faction_metrics.faction_history} />
            <FactionFlow agentsByRound={agentsByRound} rounds={rounds} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <CohesionMeter factionUpdates={factionUpdates} />
              <DefectionLog events={result.faction_metrics.alliance_events} />
            </div>
            <PanelDebateView agentsByRound={agentsByRound} rounds={rounds} />
          </div>
        </CollapsibleSection>
      )}

      {/* Agent Decisions */}
      {Object.keys(agentsByRound).length > 0 && (
        <CollapsibleSection title="Agent Decisions">
          <RoundTimeline rounds={rounds} agentsByRound={agentsByRound} />
        </CollapsibleSection>
      )}

      {/* Dynamics */}
      {((triggersEvents && triggersEvents.length > 0) || (historicalPrecedents && historicalPrecedents.length > 0)) && (
        <CollapsibleSection title="Dynamics & Context">
          <div className="space-y-4">
            {triggersEvents && triggersEvents.length > 0 && (
              <ConditionalTriggersPanel triggers={triggersEvents} />
            )}
            {historicalPrecedents && historicalPrecedents.length > 0 && (
              <HistoricalContextPanel precedents={historicalPrecedents} />
            )}
          </div>
        </CollapsibleSection>
      )}

      {/* Export row + back */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onReset}
          className="px-4 py-2 text-[13px] text-[#8B8B8B] hover:text-[#0F0F0F] border border-[#E5E5E5] hover:border-[#D0D0D0] rounded-[6px] transition-colors"
        >
          ← New Simulation
        </button>
        {runId && <ExportButton runId={runId} />}
      </div>
    </div>
  );
}
