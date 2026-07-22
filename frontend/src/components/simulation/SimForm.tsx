import { useState } from "react";
import { StakeholderPanel } from "./StakeholderPanel";
import { PrecedentPanel } from "./PrecedentPanel";
import type { SimulationConfig, CustomStakeholder, HistoricalPrecedent } from "../../types";

interface Props {
  onSubmit: (config: SimulationConfig) => void;
  disabled: boolean;
}

const EXAMPLES = [
  "Launch a 4-day work week policy at a 500-person company",
  "Release an AI code assistant as a paid SaaS product",
  "Propose a carbon tax in a developing economy",
  "Acquire a competitor during an economic downturn",
  "Migrate a monolith to microservices mid-sprint",
];

export function SimForm({ onSubmit, disabled }: Props) {
  const [stimulus, setStimulus] = useState("");
  const [agentCount, setAgentCount] = useState(5);
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("quick");
  const [mode, setMode] = useState<"collaborative" | "adversarial">("collaborative");
  const [customStakeholders, setCustomStakeholders] = useState<CustomStakeholder[]>([]);
  const [historicalPrecedents, setHistoricalPrecedents] = useState<HistoricalPrecedent[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!stimulus.trim()) return;
    const validStakeholders = customStakeholders.filter(
      (s) => s.role.trim() && s.description.trim()
    );
    const validPrecedents = historicalPrecedents.filter(
      (p) => p.title.trim() && p.summary.trim()
    );
    onSubmit({
      stimulus: stimulus.trim(),
      agent_count: agentCount,
      depth,
      mode,
      custom_stakeholders: validStakeholders.length > 0 ? validStakeholders : undefined,
      historical_precedents: validPrecedents.length > 0 ? validPrecedents : undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Main input */}
      <div className="space-y-3">
        <label className="block text-[16px] font-medium text-[#0F0F0F] tracking-[-0.01em]">
          What decision do you want to test?
        </label>
        <textarea
          value={stimulus}
          onChange={(e) => setStimulus(e.target.value)}
          disabled={disabled}
          placeholder="e.g. We're considering launching a freemium tier for our B2B product to accelerate growth, but it might cannibalize paid conversions..."
          rows={5}
          className="w-full px-4 py-3.5 text-[14px] leading-[1.6] text-[#0F0F0F] placeholder:text-[#B0B0B0] bg-white border border-[#E5E5E5] rounded-[10px] resize-none focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-colors disabled:opacity-50"
        />

        {/* Example chips */}
        {!stimulus && (
          <div className="flex flex-wrap gap-2">
            <span className="text-[11px] text-[#B0B0B0] self-center mr-1">Try:</span>
            {EXAMPLES.slice(0, 3).map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => setStimulus(ex)}
                disabled={disabled}
                className="px-3 py-1.5 text-[12px] text-[#6B6B6B] bg-[#F5F5F5] hover:bg-[#EBEBEB] rounded-[6px] transition-colors disabled:opacity-50 text-left leading-snug"
              >
                {ex}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-3 pt-1">
        {/* Agents */}
        <div className="flex items-center gap-2 px-3 py-2 bg-[#FAFAFA] border border-[#F0F0F0] rounded-[8px]">
          <span className="text-[11px] text-[#8B8B8B] uppercase tracking-wide">Agents</span>
          <input
            type="number"
            min={2}
            max={20}
            value={agentCount}
            onChange={(e) => setAgentCount(Number(e.target.value))}
            disabled={disabled}
            className="w-[40px] text-[13px] font-['JetBrains_Mono'] font-medium text-[#0F0F0F] bg-transparent border-none focus:outline-none text-center disabled:opacity-50"
          />
        </div>

        {/* Depth */}
        <div className="flex items-center gap-2 px-3 py-2 bg-[#FAFAFA] border border-[#F0F0F0] rounded-[8px]">
          <span className="text-[11px] text-[#8B8B8B] uppercase tracking-wide">Depth</span>
          <select
            value={depth}
            onChange={(e) => setDepth(e.target.value as "quick" | "standard" | "deep")}
            disabled={disabled}
            className="text-[13px] font-medium text-[#0F0F0F] bg-transparent border-none focus:outline-none cursor-pointer disabled:opacity-50"
          >
            <option value="quick">Quick</option>
            <option value="standard">Standard</option>
            <option value="deep">Deep</option>
          </select>
        </div>

        {/* Mode */}
        <div className="flex items-center gap-2 px-3 py-2 bg-[#FAFAFA] border border-[#F0F0F0] rounded-[8px]">
          <span className="text-[11px] text-[#8B8B8B] uppercase tracking-wide">Mode</span>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as "collaborative" | "adversarial")}
            disabled={disabled}
            className="text-[13px] font-medium text-[#0F0F0F] bg-transparent border-none focus:outline-none cursor-pointer disabled:opacity-50"
          >
            <option value="collaborative">Collaborative</option>
            <option value="adversarial">Adversarial</option>
          </select>
        </div>

        {/* Advanced toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="px-3 py-2 text-[11px] text-[#8B8B8B] uppercase tracking-wide hover:text-[#0F0F0F] transition-colors"
        >
          {showAdvanced ? "− Less" : "+ More"}
        </button>

        {/* Submit */}
        <button
          type="submit"
          disabled={disabled || !stimulus.trim()}
          className="ml-auto px-6 py-2.5 text-[14px] font-medium bg-[#0F0F0F] text-white rounded-[8px] hover:bg-[#2A2A2A] transition-all duration-150 hover:shadow-[0_4px_12px_rgba(0,0,0,0.15)] disabled:opacity-40 disabled:hover:shadow-none disabled:hover:bg-[#0F0F0F]"
        >
          Run Simulation →
        </button>
      </div>

      {/* Advanced options */}
      {showAdvanced && (
        <div className="pt-3 border-t border-[#F0F0F0] space-y-4 animate-fade-in">
          <StakeholderPanel
            stakeholders={customStakeholders}
            onChange={setCustomStakeholders}
            disabled={disabled}
          />
          <PrecedentPanel
            precedents={historicalPrecedents}
            onChange={setHistoricalPrecedents}
            disabled={disabled}
          />
        </div>
      )}
    </form>
  );
}
