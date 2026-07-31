import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import { extractRecommendation } from "../../lib/extractRecommendation";
import type { SimulationResult } from "../../types";

interface Props {
  result: SimulationResult;
  scenarioName: string;
  stimulus?: string;
}

function getVerdictStyle(verdict: string) {
  const v = verdict.toLowerCase();
  if (v.includes("resilient")) return { color: "#4ADE80", label: "Resilient" };
  if (v.includes("fragile")) return { color: "#EF4444", label: "Fragile" };
  if (v.includes("moderate")) return { color: "#FBBF24", label: "Moderate" };
  return { color: "#C4B5FD", label: verdict };
}

export function ShareCard({ result, scenarioName, stimulus }: Props) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [generating, setGenerating] = useState(false);

  const verdict = result.resilience_metrics?.verdict || result.verdict || "Unknown";
  const verdictStyle = getVerdictStyle(verdict);
  const stability = result.resilience_metrics?.decision_stability;
  const recommendation = extractRecommendation(result.report_md);
  const duration = result.timings?.total;

  // Try to get agent count from report or metrics
  const agentCount = (() => {
    if (result.quantitative_metrics?.vote_tally) {
      const firstRound = Object.values(result.quantitative_metrics.vote_tally)[0];
      if (firstRound) return Object.values(firstRound).reduce((a, b) => a + b, 0);
    }
    return null;
  })();

  // Display question — prefer short stimulus, fallback to scenario name
  const displayQuestion = stimulus && stimulus.length < 120 ? stimulus : scenarioName;

  const handleDownload = async () => {
    if (!cardRef.current) return;
    setGenerating(true);
    try {
      const dataUrl = await toPng(cardRef.current, {
        pixelRatio: 2,
        width: 1200,
        height: 630,
        style: {
          transform: "scale(1)",
          transformOrigin: "top left",
        },
      });
      const link = document.createElement("a");
      link.download = `simulateai-${scenarioName.slice(0, 30).replace(/\s+/g, "-").toLowerCase()}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error("Share card generation failed:", err);
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = async () => {
    if (!cardRef.current) return;
    setGenerating(true);
    try {
      const dataUrl = await toPng(cardRef.current, {
        pixelRatio: 2,
        width: 1200,
        height: 630,
      });
      const blob = await (await fetch(dataUrl)).blob();
      await navigator.clipboard.write([
        new ClipboardItem({ "image/png": blob }),
      ]);
    } catch (err) {
      console.error("Copy to clipboard failed:", err);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Card preview (scaled down for display) */}
      <div className="border border-[#E5E5E5] rounded-[10px] overflow-hidden">
        <div className="overflow-hidden" style={{ maxHeight: "340px" }}>
          <div style={{ transform: "scale(0.5)", transformOrigin: "top left", width: "200%", height: "200%" }}>
            {/* The actual 1200x630 card */}
            <div
              ref={cardRef}
              style={{
                width: "1200px",
                height: "630px",
                padding: "64px",
                backgroundColor: "#0A0A0A",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                fontFamily: "'Inter', system-ui, sans-serif",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {/* Subtle grid */}
              <div style={{
                position: "absolute",
                inset: 0,
                opacity: 0.04,
                backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
                backgroundSize: "60px 60px",
              }} />

              {/* Content */}
              <div style={{ position: "relative", zIndex: 1 }}>
                {/* Logo */}
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "48px" }}>
                  <img src="/logo-mark.svg" style={{ height: "28px", filter: "brightness(0) invert(1)" }} />
                  <span style={{ fontSize: "18px", fontWeight: 500, color: "#ffffff", letterSpacing: "-0.01em" }}>SimulateAI</span>
                </div>

                {/* Question */}
                <p style={{
                  fontSize: "32px",
                  fontWeight: 600,
                  color: "#ffffff",
                  lineHeight: 1.3,
                  letterSpacing: "-0.02em",
                  maxWidth: "900px",
                  marginBottom: "28px",
                }}>
                  {displayQuestion}
                </p>

                {/* Recommendation */}
                {recommendation && (
                  <p style={{
                    fontSize: "20px",
                    color: "#9CA3AF",
                    lineHeight: 1.5,
                    maxWidth: "850px",
                  }}>
                    {recommendation}
                  </p>
                )}
              </div>

              {/* Bottom row */}
              <div style={{ position: "relative", zIndex: 1, display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
                {/* Verdict + metrics */}
                <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
                  <span style={{
                    fontSize: "28px",
                    fontWeight: 700,
                    color: verdictStyle.color,
                    letterSpacing: "-0.01em",
                  }}>
                    {verdictStyle.label}
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: "16px", color: "#6B7280", fontSize: "16px", fontFamily: "'JetBrains Mono', monospace" }}>
                    {stability !== undefined && <span>{(stability * 100).toFixed(0)}% stability</span>}
                    {agentCount && <span>{agentCount} agents</span>}
                    {duration && <span>{Math.round(duration)}s</span>}
                  </div>
                </div>

                {/* URL */}
                <span style={{ fontSize: "14px", color: "#4B5563", fontFamily: "'JetBrains Mono', monospace" }}>
                  simulate-ai-production.up.railway.app
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleDownload}
          disabled={generating}
          className="flex-1 px-4 py-2.5 text-[13px] font-medium bg-[#0F0F0F] text-white rounded-[8px] hover:bg-[#2A2A2A] transition-colors disabled:opacity-50"
        >
          {generating ? "Generating..." : "Download PNG"}
        </button>
        <button
          onClick={handleCopy}
          disabled={generating}
          className="flex-1 px-4 py-2.5 text-[13px] font-medium border border-[#E5E5E5] text-[#0F0F0F] rounded-[8px] hover:bg-[#FAFAFA] transition-colors disabled:opacity-50"
        >
          Copy to clipboard
        </button>
      </div>
    </div>
  );
}
