import { useState } from "react";
import type { SimulationConfig } from "../../types";

interface Props {
  onSubmit: (config: SimulationConfig) => void;
  disabled: boolean;
}

export function SimForm({ onSubmit, disabled }: Props) {
  const [stimulus, setStimulus] = useState("");
  const [agentCount, setAgentCount] = useState(5);
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("standard");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!stimulus.trim()) return;
    onSubmit({ stimulus: stimulus.trim(), agent_count: agentCount, depth });
  };

  return (
    <form onSubmit={handleSubmit} className="border border-[#E5E5E5] rounded-[6px] bg-white p-4 space-y-4">
      <div>
        <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-1.5">
          Stimulus
        </label>
        <textarea
          value={stimulus}
          onChange={(e) => setStimulus(e.target.value)}
          disabled={disabled}
          placeholder="Describe the scenario to simulate..."
          rows={4}
          className="w-full px-3 py-2.5 text-[14px] leading-relaxed border border-[#E5E5E5] rounded-[6px] bg-white resize-none focus:outline-none focus:border-[#D0D0D0] disabled:opacity-50 placeholder:text-[#9B9B9B]"
        />
      </div>
      <div className="flex items-end gap-4">
        <div>
          <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-1.5">
            Agents
          </label>
          <input
            type="number"
            min={1}
            max={20}
            value={agentCount}
            onChange={(e) => setAgentCount(Number(e.target.value))}
            disabled={disabled}
            className="w-20 px-3 py-2 text-[14px] font-['JetBrains_Mono'] border border-[#E5E5E5] rounded-[6px] bg-white focus:outline-none focus:border-[#D0D0D0] disabled:opacity-50"
          />
        </div>
        <div>
          <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider mb-1.5">
            Depth
          </label>
          <select
            value={depth}
            onChange={(e) => setDepth(e.target.value as "quick" | "standard" | "deep")}
            disabled={disabled}
            className="px-3 py-2 text-[14px] border border-[#E5E5E5] rounded-[6px] bg-white focus:outline-none focus:border-[#D0D0D0] disabled:opacity-50"
          >
            <option value="quick">Quick</option>
            <option value="standard">Standard</option>
            <option value="deep">Deep</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={disabled || !stimulus.trim()}
          className="ml-auto px-5 py-2 text-[14px] font-medium bg-[#1A1A1A] text-white rounded-[6px] hover:bg-[#333] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          Run Simulation
        </button>
      </div>
    </form>
  );
}
