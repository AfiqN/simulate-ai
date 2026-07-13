import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AdversarialResult, ArgumentClaimResult } from "../../types";

interface Props {
  result: AdversarialResult;
}

function getSurvivalLabel(rate: number): { text: string; color: string } {
  if (rate >= 0.7) return { text: "High Credibility", color: "#16653A" };
  if (rate >= 0.4) return { text: "Mixed Signal", color: "#6B5C1A" };
  return { text: "Low Credibility", color: "#8B1A1A" };
}

function getStatusBadge(status: ArgumentClaimResult["status"]) {
  switch (status) {
    case "standing":
      return { label: "Standing", bg: "#ECFDF5", text: "#16653A", border: "#A7F3D0" };
    case "amended":
      return { label: "Amended", bg: "#FFFBEB", text: "#6B5C1A", border: "#FDE68A" };
    case "defeated":
      return { label: "Defeated", bg: "#FEF2F2", text: "#8B1A1A", border: "#FECACA" };
  }
}

function getSeverityBadge(severity: string) {
  switch (severity) {
    case "fatal":
      return { label: "Fatal", bg: "#FEF2F2", text: "#8B1A1A" };
    case "serious":
      return { label: "Serious", bg: "#FFFBEB", text: "#6B5C1A" };
    case "minor":
      return { label: "Minor", bg: "#F0F9FF", text: "#1E40AF" };
    default:
      return { label: severity || "Unknown", bg: "#F5F5F5", text: "#6B6B6B" };
  }
}

function ClaimCard({ claim }: { claim: ArgumentClaimResult }) {
  const [expanded, setExpanded] = useState(false);
  const statusBadge = getStatusBadge(claim.status);

  return (
    <div
      className="border border-[#E5E5E5] rounded-md p-3 hover:border-[#D0D0D0] transition-colors cursor-pointer"
      onClick={() => setExpanded(!expanded)}
      role="button"
      aria-expanded={expanded}
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setExpanded(!expanded); }}
    >
      <div className="flex items-start gap-2">
        <span
          className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded-sm shrink-0 mt-0.5"
          style={{ backgroundColor: statusBadge.bg, color: statusBadge.text, border: `1px solid ${statusBadge.border}` }}
        >
          {statusBadge.label}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-[11px] text-[#9B9B9B] uppercase tracking-wider">
              {claim.archetype}
            </span>
          </div>
          <p className="text-[13px] text-[#0F0F0F] leading-snug">
            "{claim.status === "amended" && claim.amended_claim ? claim.amended_claim : claim.claim_text}"
          </p>
        </div>
        <span className="text-[#9B9B9B] text-[12px] shrink-0 mt-1">
          {expanded ? "▾" : "▸"}
        </span>
      </div>

      {expanded && (
        <div className="mt-3 pl-7 space-y-2 border-t border-[#E5E5E5] pt-3">
          {claim.evidence && (
            <div>
              <span className="text-[10px] text-[#9B9B9B] uppercase tracking-wider block mb-0.5">Evidence</span>
              <p className="text-[12px] text-[#6B6B6B]">{claim.evidence}</p>
            </div>
          )}
          {claim.attack_text && (
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-[10px] text-[#9B9B9B] uppercase tracking-wider">Attack</span>
                {claim.attack_severity && (() => {
                  const sev = getSeverityBadge(claim.attack_severity);
                  return (
                    <span
                      className="text-[9px] font-medium px-1 py-0.5 rounded-sm"
                      style={{ backgroundColor: sev.bg, color: sev.text }}
                    >
                      {sev.label}
                    </span>
                  );
                })()}
              </div>
              <p className="text-[12px] text-[#6B6B6B]">{claim.attack_text}</p>
            </div>
          )}
          {claim.defense_text && (
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-[10px] text-[#9B9B9B] uppercase tracking-wider">Defense</span>
                <span className="text-[10px] text-[#6B6B6B]">({claim.defense_response})</span>
              </div>
              <p className="text-[12px] text-[#6B6B6B]">{claim.defense_text}</p>
            </div>
          )}
          {claim.status === "amended" && claim.amended_claim && (
            <div>
              <span className="text-[10px] text-[#9B9B9B] uppercase tracking-wider block mb-0.5">Amended Claim</span>
              <p className="text-[12px] text-[#6B5C1A] font-medium">"{claim.amended_claim}"</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function AdversarialResultPanel({ result }: Props) {
  const label = getSurvivalLabel(result.survival_rate);
  const amendedCount = result.claims.filter((c) => c.status === "amended").length;

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">
          Argument Survival Analysis
        </h3>

        {/* Survival rate gauge */}
        <div className="flex items-baseline gap-2 mb-4">
          <span
            className="text-[28px] font-['JetBrains_Mono'] font-medium tabular-nums"
            style={{ color: label.color }}
          >
            {(result.survival_rate * 100).toFixed(0)}%
          </span>
          <span className="text-[13px] font-medium" style={{ color: label.color }}>
            {label.text}
          </span>
          <span className="text-[12px] text-[#9B9B9B] ml-2">
            survival rate
          </span>
        </div>

        {/* Stats row */}
        <div className="flex gap-3 mb-4">
          <Badge variant="outline" className="text-[11px] font-['JetBrains_Mono'] border-[#A7F3D0] text-[#16653A] bg-[#ECFDF5]">
            {result.surviving_count} survived
          </Badge>
          {amendedCount > 0 && (
            <Badge variant="outline" className="text-[11px] font-['JetBrains_Mono'] border-[#FDE68A] text-[#6B5C1A] bg-[#FFFBEB]">
              {amendedCount} amended
            </Badge>
          )}
          <Badge variant="outline" className="text-[11px] font-['JetBrains_Mono'] border-[#FECACA] text-[#8B1A1A] bg-[#FEF2F2]">
            {result.defeated_count} defeated
          </Badge>
          <span className="text-[11px] text-[#9B9B9B] self-center ml-auto">
            {result.claims.length} total claims
          </span>
        </div>

        {/* Key defeats summary */}
        {result.key_defeats.length > 0 && (
          <div className="bg-[#FEF2F2] border border-[#FECACA] rounded-md p-3 mb-4">
            <span className="text-[10px] text-[#8B1A1A] uppercase tracking-wider font-medium block mb-1.5">
              Key Defeats
            </span>
            <ul className="space-y-1">
              {result.key_defeats.slice(0, 3).map((d, i) => (
                <li key={i} className="text-[12px] text-[#6B6B6B] leading-snug">
                  • {d}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {/* Claims list */}
      <Card className="p-4">
        <h3 className="text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-3">
          Claims Detail
        </h3>
        <div className="space-y-2">
          {result.claims.map((claim, i) => (
            <ClaimCard key={`${claim.agent_id}-${i}`} claim={claim} />
          ))}
        </div>
      </Card>
    </div>
  );
}
