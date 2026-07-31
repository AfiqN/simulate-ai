import { useState, useRef, useCallback } from "react";
import { generateReport } from "../../lib/pdfReport";
import { InfoTip } from "@/components/ui/infotip";
import { ShareCard } from "../share/ShareCard";
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
  onRefine?: (originalStimulus: string, previousVerdict: string, scenarioName: string, depth: string, agents: number) => void;
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


export function ResultsView({ result, rounds, agentsByRound, schema, factionUpdates, triggersEvents, historicalPrecedents, adversarialResult, runId, onReset, onRefine }: Props) {
  const [exporting, setExporting] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const [showShareCard, setShowShareCard] = useState(false);
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
            <button
              onClick={() => setShowShareCard(!showShareCard)}
              className="px-3 py-1.5 text-[12px] text-[#8B8B8B] border border-[#3A3A3A] rounded-[6px] hover:border-[#6B6B6B] hover:text-white transition-colors"
            >
              {showShareCard ? "Hide card" : "Share image"}
            </button>
            {runId && (
              <button
                onClick={handleShare}
                className="px-3 py-1.5 text-[12px] text-[#8B8B8B] border border-[#3A3A3A] rounded-[6px] hover:border-[#6B6B6B] hover:text-white transition-colors"
              >
                {shareCopied ? "Copied!" : "Share link"}
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

        {/* Share card modal */}
        {showShareCard && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowShareCard(false)}>
            <div className="bg-white rounded-[12px] p-6 max-w-[660px] w-full mx-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-[15px] font-medium text-[#0F0F0F]">Share as image</h3>
                <button onClick={() => setShowShareCard(false)} className="text-[#8B8B8B] hover:text-[#0F0F0F] text-[18px]">&times;</button>
              </div>
              <ShareCard
                result={result}
                scenarioName={schema?.scenario_name || result.scenario_name || "Simulation"}
                stimulus={schema?.scenario_name || result.scenario_name}
              />
            </div>
          </div>
        )}

        {/* Verdict + key metrics */}
        <div className="flex flex-wrap items-end gap-8">
          <div>
            <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">
              <InfoTip term="Verdict">
                <strong>Resilient:</strong> Decision survives crisis — majority hold position.<br/>
                <strong>Moderate:</strong> Some agents flip under pressure — viable but risky.<br/>
                <strong>Fragile:</strong> Coalition fractures under stress — needs rethinking.<br/>
                <strong>Indeterminate:</strong> Not enough data to conclude.
              </InfoTip>
            </p>
            <p className={`text-[28px] sm:text-[32px] font-semibold tracking-[-0.02em] ${verdict.toLowerCase().includes("resilient") ? "text-[#4ADE80]" : verdict.toLowerCase().includes("fragile") ? "text-[#EF4444]" : "text-[#C4B5FD]"}`}>
              {verdict}
            </p>
          </div>
          {stability !== undefined && (
            <div>
              <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">
                <InfoTip term="Stability">
                  Percentage of agents who maintained their position after the crisis event. Higher = more stable decision.
                </InfoTip>
              </p>
              <p className="text-[20px] font-['JetBrains_Mono'] font-medium text-white tabular-nums">
                {(stability * 100).toFixed(0)}%
              </p>
            </div>
          )}
          {drift !== undefined && (
            <div>
              <p className="text-[10px] text-[#6B6B6B] uppercase tracking-wider mb-1">
                <InfoTip term="Utility Drift">
                  Average shift in agent confidence between rounds. Positive = agents became more supportive. Negative = lost confidence.
                </InfoTip>
              </p>
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

      {/* What if... refine */}
      {onRefine && (
        <div className="border border-[#E5E5E5] rounded-[10px] p-5 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-[15px] font-medium text-[#0F0F0F]">What if...?</h3>
              <p className="text-[13px] text-[#6B6B6B] mt-0.5">Test a variation of this scenario with different assumptions.</p>
            </div>
            <button
              onClick={() => onRefine(
                result.scenario_name || schema?.scenario_name || "",
                verdict,
                schema?.scenario_name || result.scenario_name || "Simulation",
                "standard",
                totalAgents || 5
              )}
              className="px-5 py-2.5 text-[13px] font-medium bg-[#0F0F0F] text-white rounded-[8px] hover:bg-[#2A2A2A] transition-colors shrink-0"
            >
              Refine →
            </button>
          </div>
        </div>
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
