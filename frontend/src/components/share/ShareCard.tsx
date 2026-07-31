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
                padding: "0",
                backgroundColor: "#0A0A0A",
                display: "flex",
                flexDirection: "column",
                fontFamily: "'Inter', system-ui, sans-serif",
                position: "relative",
                overflow: "hidden",
              }}
            >
              {/* Top accent bar */}
              <div style={{ height: "4px", background: verdictStyle.color }} />

              {/* Background dot pattern */}
              <div style={{
                position: "absolute",
                inset: 0,
                opacity: 0.06,
                backgroundImage: "radial-gradient(circle at 1px 1px, #ffffff 1px, transparent 0)",
                backgroundSize: "32px 32px",
              }} />

              {/* Main content — compact, no wasted space */}
              <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-between", padding: "44px 56px 32px" }}>
                {/* Top: logo + verdict + scenario */}
                <div>
                  {/* Header row */}
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "32px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <img src="/logo-mark.svg" style={{ height: "22px", filter: "brightness(0) invert(1)" }} />
                      <span style={{ fontSize: "15px", fontWeight: 500, color: "#9CA3AF" }}>SimulateAI</span>
                    </div>
                    <div style={{
                      padding: "6px 14px",
                      borderRadius: "6px",
                      backgroundColor: verdictStyle.color + "18",
                      border: `1px solid ${verdictStyle.color}40`,
                    }}>
                      <span style={{ fontSize: "13px", fontWeight: 700, color: verdictStyle.color, letterSpacing: "0.05em", textTransform: "uppercase" }}>
                        {verdictStyle.label}
                        {stability !== undefined && ` · ${(stability * 100).toFixed(0)}%`}
                      </span>
                    </div>
                  </div>

                  {/* Scenario */}
                  <span style={{ fontSize: "11px", color: "#6B7280", letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 500 }}>
                    Scenario tested
                  </span>
                  <p style={{
                    fontSize: "42px",
                    fontWeight: 700,
                    color: "#ffffff",
                    lineHeight: 1.2,
                    letterSpacing: "-0.025em",
                    maxWidth: "950px",
                    marginTop: "10px",
                  }}>
                    {displayQuestion}
                  </p>
                </div>

                {/* Bottom: recommendation + URL */}
                <div style={{ borderTop: "1px solid #1F2937", paddingTop: "20px", display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
                  {recommendation ? (
                    <div style={{ maxWidth: "850px" }}>
                      <span style={{ fontSize: "11px", color: "#6B7280", letterSpacing: "0.08em", textTransform: "uppercase", fontWeight: 500 }}>
                        Key recommendation
                      </span>
                      <p style={{
                        fontSize: "20px",
                        color: "#D1D5DB",
                        lineHeight: 1.45,
                        marginTop: "6px",
                      }}>
                        {recommendation}
                      </p>
                    </div>
                  ) : (
                    <div />
                  )}
                  <span style={{ fontSize: "12px", color: "#374151", fontFamily: "'JetBrains Mono', monospace", flexShrink: 0 }}>
                    simulate-ai-production.up.railway.app
                  </span>
                </div>
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
