import { useState } from "react";
import { Plus, X, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { HistoricalPrecedent } from "../../types";

interface Props {
  precedents: HistoricalPrecedent[];
  onChange: (precedents: HistoricalPrecedent[]) => void;
  disabled: boolean;
}

const EMPTY_PRECEDENT: HistoricalPrecedent = {
  title: "",
  year: null,
  summary: "",
  outcome: "",
  relevance: "",
  domain: "",
};

export function PrecedentPanel({ precedents, onChange, disabled }: Props) {
  const [expanded, setExpanded] = useState(false);

  const handleAdd = () => {
    if (precedents.length >= 5) return;
    onChange([...precedents, { ...EMPTY_PRECEDENT }]);
    setExpanded(true);
  };

  const handleRemove = (index: number) => {
    const updated = precedents.filter((_, i) => i !== index);
    onChange(updated);
    if (updated.length === 0) setExpanded(false);
  };

  const handleUpdate = (index: number, field: keyof HistoricalPrecedent, value: string | number | null) => {
    const updated = [...precedents];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-[11px] text-[#6B6B6B] uppercase tracking-wider font-medium hover:text-[#0F0F0F] transition-colors"
        >
          <BookOpen size={12} />
          Historical Precedents
          {precedents.length > 0 && (
            <span className="text-[10px] bg-[#F5F5F5] text-[#6B6B6B] rounded-[3px] px-1.5 py-0.5 ml-1">
              {precedents.length}
            </span>
          )}
        </button>
        {expanded && precedents.length < 5 && (
          <Button type="button" size="sm" variant="outline" onClick={handleAdd} disabled={disabled}>
            <Plus size={11} className="mr-1" />
            Add
          </Button>
        )}
      </div>

      {!expanded && precedents.length === 0 && (
        <button
          type="button"
          onClick={handleAdd}
          disabled={disabled}
          className="w-full py-3 border border-dashed border-[#E5E5E5] rounded-[6px] text-[12px] text-[#9B9B9B] hover:border-[#D0D0D0] hover:text-[#6B6B6B] transition-colors"
        >
          + Add historical precedents to ground the simulation
        </button>
      )}

      {expanded && (
        <div className="space-y-3">
          {precedents.map((p, i) => (
            <div
              key={i}
              className="relative p-3 border border-[#E5E5E5] rounded-[6px] space-y-2 animate-fade-in"
            >
              <button
                type="button"
                onClick={() => handleRemove(i)}
                disabled={disabled}
                className="absolute top-2 right-2 p-1 rounded-[4px] hover:bg-[#FEF2F2] transition-colors"
              >
                <X size={12} className="text-[#9B9B9B] hover:text-[#8B1A1A]" />
              </button>

              <div className="grid grid-cols-[1fr_80px_120px] gap-2">
                <Input
                  value={p.title}
                  onChange={(e) => handleUpdate(i, "title", e.target.value)}
                  placeholder="Event title"
                  disabled={disabled}
                  className="text-[13px]"
                />
                <Input
                  type="number"
                  value={p.year ?? ""}
                  onChange={(e) => handleUpdate(i, "year", e.target.value ? Number(e.target.value) : null)}
                  placeholder="Year"
                  disabled={disabled}
                  className="text-[13px] font-['JetBrains_Mono']"
                />
                <Input
                  value={p.domain || ""}
                  onChange={(e) => handleUpdate(i, "domain", e.target.value)}
                  placeholder="Domain"
                  disabled={disabled}
                  className="text-[13px]"
                />
              </div>

              <Textarea
                value={p.summary}
                onChange={(e) => handleUpdate(i, "summary", e.target.value)}
                placeholder="Brief description of what happened..."
                disabled={disabled}
                rows={2}
                className="text-[12px]"
              />

              <div className="grid grid-cols-2 gap-2">
                <Input
                  value={p.outcome || ""}
                  onChange={(e) => handleUpdate(i, "outcome", e.target.value)}
                  placeholder="Outcome"
                  disabled={disabled}
                  className="text-[12px]"
                />
                <Input
                  value={p.relevance || ""}
                  onChange={(e) => handleUpdate(i, "relevance", e.target.value)}
                  placeholder="Why it's relevant"
                  disabled={disabled}
                  className="text-[12px]"
                />
              </div>
            </div>
          ))}

          {precedents.length === 0 && (
            <p className="text-[11px] text-[#9B9B9B] text-center py-2">
              No precedents added. Click "Add" to supply historical context.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
