import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { CustomStakeholder } from "../../types";

interface Props {
  stakeholders: CustomStakeholder[];
  onChange: (stakeholders: CustomStakeholder[]) => void;
  disabled: boolean;
}

const MAX_STAKEHOLDERS = 10;

const emptyStakeholder = (): CustomStakeholder => ({
  role: "",
  description: "",
  focus_areas: [],
  constraints: [],
});

export function StakeholderPanel({ stakeholders, onChange, disabled }: Props) {
  const [expanded, setExpanded] = useState(stakeholders.length > 0);

  const addStakeholder = () => {
    if (stakeholders.length >= MAX_STAKEHOLDERS) return;
    onChange([...stakeholders, emptyStakeholder()]);
    setExpanded(true);
  };

  const removeStakeholder = (index: number) => {
    onChange(stakeholders.filter((_, i) => i !== index));
  };

  const updateField = (index: number, field: keyof CustomStakeholder, value: string | string[]) => {
    const updated = [...stakeholders];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  const handleTagInput = (
    index: number,
    field: "focus_areas" | "constraints",
    inputValue: string
  ) => {
    // Split on commas/Enter, trim, dedupe
    const tags = inputValue
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    updateField(index, field, tags);
  };

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        disabled={disabled}
        className="flex items-center gap-2 text-[11px] text-[#9B9B9B] uppercase tracking-wider font-medium hover:text-[#0F0F0F] transition-colors disabled:opacity-50"
      >
        <span className={`transition-transform ${expanded ? "rotate-90" : ""}`}>▸</span>
        Custom Stakeholders
        {stakeholders.length > 0 && (
          <span className="text-[#0F0F0F] bg-[#F5F5F5] rounded px-1.5 py-0.5 text-[10px] font-mono">
            {stakeholders.length}
          </span>
        )}
      </button>

      {expanded && (
        <div className="space-y-3 pl-3 border-l-2 border-[#E5E5E5]">
          {stakeholders.map((s, i) => (
            <div
              key={i}
              className="bg-[#FAFAFA] rounded-md p-3 space-y-2 border border-[#E5E5E5]"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-[#9B9B9B] font-mono">
                  #{i + 1}
                </span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeStakeholder(i)}
                  disabled={disabled}
                  className="h-6 px-2 text-[11px] text-[#9B9B9B] hover:text-[#8B1A1A]"
                >
                  ✕ Remove
                </Button>
              </div>

              <div className="grid grid-cols-[1fr_2fr] gap-2">
                <div>
                  <Input
                    value={s.role}
                    onChange={(e) => updateField(i, "role", e.target.value)}
                    disabled={disabled}
                    placeholder="Role (e.g. CFO)"
                    className="text-[13px]"
                  />
                </div>
                <div>
                  <Input
                    value={(s.focus_areas || []).join(", ")}
                    onChange={(e) => handleTagInput(i, "focus_areas", e.target.value)}
                    disabled={disabled}
                    placeholder="Focus areas (comma-separated)"
                    className="text-[13px]"
                  />
                </div>
              </div>

              <Textarea
                value={s.description}
                onChange={(e) => updateField(i, "description", e.target.value)}
                disabled={disabled}
                placeholder="Describe this stakeholder's personality, priorities, and stance..."
                rows={2}
                className="text-[13px]"
              />

              <Input
                value={(s.constraints || []).join(", ")}
                onChange={(e) => handleTagInput(i, "constraints", e.target.value)}
                disabled={disabled}
                placeholder="Red lines / constraints (comma-separated)"
                className="text-[13px]"
              />
            </div>
          ))}

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addStakeholder}
            disabled={disabled || stakeholders.length >= MAX_STAKEHOLDERS}
            className="w-full text-[12px]"
          >
            + Add Stakeholder
            {stakeholders.length > 0 && (
              <span className="text-[#9B9B9B] ml-1">
                ({stakeholders.length}/{MAX_STAKEHOLDERS})
              </span>
            )}
          </Button>
        </div>
      )}
    </div>
  );
}
