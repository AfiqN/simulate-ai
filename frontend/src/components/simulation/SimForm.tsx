import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { StakeholderPanel } from "./StakeholderPanel";
import { PrecedentPanel } from "./PrecedentPanel";
import type { SimulationConfig, CustomStakeholder, HistoricalPrecedent } from "../../types";

interface Props {
  onSubmit: (config: SimulationConfig) => void;
  disabled: boolean;
}

export function SimForm({ onSubmit, disabled }: Props) {
  const [stimulus, setStimulus] = useState("");
  const [agentCount, setAgentCount] = useState(5);
  const [depth, setDepth] = useState<"quick" | "standard" | "deep">("quick");
  const [mode, setMode] = useState<"collaborative" | "adversarial">("collaborative");
  const [customStakeholders, setCustomStakeholders] = useState<CustomStakeholder[]>([]);
  const [historicalPrecedents, setHistoricalPrecedents] = useState<HistoricalPrecedent[]>([]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!stimulus.trim()) return;
    // Filter out incomplete stakeholders (missing role or description)
    const validStakeholders = customStakeholders.filter(
      (s) => s.role.trim() && s.description.trim()
    );
    // Filter out incomplete precedents (missing title or summary)
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
    <Card>
      <CardContent className="p-5">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
              Stimulus
            </label>
            <Textarea
              value={stimulus}
              onChange={(e) => setStimulus(e.target.value)}
              disabled={disabled}
              placeholder="Describe the scenario to simulate..."
              rows={4}
            />
          </div>

          <div className="flex items-end gap-4">
            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
                Agents
              </label>
              <Input
                type="number"
                min={1}
                max={20}
                value={agentCount}
                onChange={(e) => setAgentCount(Number(e.target.value))}
                disabled={disabled}
                className="w-20 font-['JetBrains_Mono']"
              />
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
                Depth
              </label>
              <Select
                value={depth}
                onChange={(e) => setDepth(e.target.value as "quick" | "standard" | "deep")}
                disabled={disabled}
                className="w-[120px]"
              >
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="block text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium">
                Mode
              </label>
              <Select
                value={mode}
                onChange={(e) => setMode(e.target.value as "collaborative" | "adversarial")}
                disabled={disabled}
                className="w-[140px]"
              >
                <option value="collaborative">Collaborative</option>
                <option value="adversarial">Adversarial</option>
              </Select>
            </div>

            <Button
              type="submit"
              disabled={disabled || !stimulus.trim()}
              className="ml-auto"
              size="lg"
            >
              Run Simulation
            </Button>
          </div>

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
        </form>
      </CardContent>
    </Card>
  );
}
