import { useState, useRef, useCallback } from "react";
import { generateReport } from "../../lib/pdfReport";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { CrisisCallout } from "./CrisisCallout";
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

  // Crisis event extraction
  const crisisStress = typeof result.crisis_event === "object"
    ? result.crisis_event?.stress
    : typeof result.crisis_event === "string"
    ? result.crisis_event
    : null;
  const crisisValidation = typeof result.crisis_event === "object"
    ? result.crisis_event?.validation
    : null;

  return (
    <div className="space-y-6">
      {/* Actions bar */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={onReset}
          className="px-4 py-2 text-[13px] border border-[#E5E5E5] rounded-[6px] text-[#6B6B6B] hover:border-[#D0D0D0] hover:text-[#0F0F0F] transition-colors"
        >
          ← New Simulation
        </button>
        {runId && (
          <button
            onClick={handleShare}
            className="px-4 py-2 text-[13px] border border-[#E5E5E5] rounded-[6px] text-[#6B6B6B] hover:border-[#D0D0D0] hover:text-[#0F0F0F] transition-colors"
          >
            {shareCopied ? "Link copied!" : "Share"}
          </button>
        )}
        {runId && <ExportButton runId={runId} />}
      </div>

      {/* PDF-capturable area */}
      <div ref={reportRef} className="space-y-6">
        {/* Executive Summary */}
        <ExecutiveSummary
          result={result}
          rounds={rounds}
          scenarioName={schema?.scenario_name}
          onExportPdf={handleExportPdf}
          exporting={exporting}
        />

        {/* Crisis Callout */}
        {crisisStress && (
          <CrisisCallout stressEvent={crisisStress} validationEvent={crisisValidation} />
        )}

        {/* Metrics - rebalanced layout */}
        <div className="space-y-4">
          <h2 className="text-[15px] font-medium tracking-[-0.02em]">Metrics</h2>

          {/* Vote tally - full width */}
          <VoteTally rounds={rounds} />

          {/* Dimension chart - full width */}
          {result.quantitative_metrics?.dimension_stats && (
            <DimensionChart stats={result.quantitative_metrics.dimension_stats} />
          )}

          {/* Consensus + Swing side by side */}
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

        {/* Adversarial Debate Results (replaces Coalition Dynamics in adversarial mode) */}
        {adversarialResult && adversarialResult.claims.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-[15px] font-medium tracking-[-0.02em]">Adversarial Debate</h2>
            <AdversarialResultPanel result={adversarialResult} />
          </div>
        )}

        {/* Coalition Dynamics (collaborative mode only) */}
        {!adversarialResult && result.faction_metrics && (
          <div className="space-y-4">
            <h2 className="text-[15px] font-medium tracking-[-0.02em]">Coalition Dynamics</h2>

            {/* Faction size over rounds - full width */}
            <FactionTimeline history={result.faction_metrics.faction_history} />

            {/* Alluvial flow - full width */}
            <FactionFlow agentsByRound={agentsByRound} rounds={rounds} />

            {/* Cohesion + Defections side by side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <CohesionMeter factionUpdates={factionUpdates} />
              <DefectionLog events={result.faction_metrics.alliance_events} />
            </div>

            {/* Panel debate - deep mode only */}
            <PanelDebateView agentsByRound={agentsByRound} rounds={rounds} />
          </div>
        )}

        {/* Round Timeline with all agents */}
        {Object.keys(agentsByRound).length > 0 && (
          <div>
            <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-3">Agent Decisions</h2>
            <RoundTimeline rounds={rounds} agentsByRound={agentsByRound} />
          </div>
        )}

        {/* Dynamics: Triggers + Historical Context */}
        {((triggersEvents && triggersEvents.length > 0) || (historicalPrecedents && historicalPrecedents.length > 0)) && (
          <div className="space-y-4">
            <h2 className="text-[15px] font-medium tracking-[-0.02em]">Dynamics</h2>
            {triggersEvents && triggersEvents.length > 0 && (
              <ConditionalTriggersPanel triggers={triggersEvents} />
            )}
            {historicalPrecedents && historicalPrecedents.length > 0 && (
              <HistoricalContextPanel precedents={historicalPrecedents} />
            )}
          </div>
        )}

        {/* Report markdown + raw data */}
        <div>
          <h2 className="text-[15px] font-medium tracking-[-0.02em] mb-3">Analysis Report</h2>
          <ReportSection result={result} />
        </div>
      </div>
    </div>
  );
}
