import { useState } from "react";
import type { SchemaData } from "../../types";

interface Props {
  schema: SchemaData;
  onApprove: () => void;
}

export function SchemaApproval({ schema, onApprove }: Props) {
  const [approving, setApproving] = useState(false);

  const handleApprove = () => {
    setApproving(true);
    onApprove();
  };

  return (
    <div className="border border-[#D97706]/30 rounded-[6px] bg-[#FFFBEB] p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-[#D97706] uppercase tracking-wider font-medium">Schema Pending Approval</span>
          <span className="text-[11px] text-[#9B9B9B]">Auto-approves in 120s</span>
        </div>
        <button
          onClick={handleApprove}
          disabled={approving}
          className="px-4 py-1.5 text-[13px] font-medium bg-[#1A1A1A] text-white rounded-[6px] hover:bg-[#333] transition-colors disabled:opacity-50"
        >
          {approving ? "Approving..." : "Approve & Continue"}
        </button>
      </div>

      <div className="space-y-3">
        <div>
          <h3 className="text-[14px] font-medium text-[#0F0F0F]">{schema.scenario_name}</h3>
        </div>

        <div>
          <span className="text-[11px] text-[#6B6B6B] uppercase tracking-wider">Actions</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {schema.actions.map((a) => (
              <span
                key={a.name}
                className={`px-2 py-0.5 text-[11px] rounded-[4px] ${
                  a.is_terminal
                    ? "bg-[#8B1A1A]/10 text-[#8B1A1A]"
                    : "bg-[#F5F5F5] text-[#6B6B6B]"
                }`}
                title={a.description || a.name}
              >
                {a.name}{a.is_terminal ? " ⊘" : ""}
              </span>
            ))}
          </div>
        </div>

        <div>
          <span className="text-[11px] text-[#6B6B6B] uppercase tracking-wider">Evaluation Dimensions</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {schema.evaluation_dimensions.map((dim) => (
              <span key={dim} className="px-2 py-0.5 text-[11px] bg-[#F5F5F5] text-[#6B6B6B] rounded-[4px]">
                {dim}
              </span>
            ))}
          </div>
        </div>

        {schema.state_vocabulary && schema.state_vocabulary.length > 0 && (
          <div>
            <span className="text-[11px] text-[#6B6B6B] uppercase tracking-wider">State Vocabulary</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {schema.state_vocabulary.map((s) => (
                <span key={s} className="px-2 py-0.5 text-[11px] bg-[#EEF2FF] text-[#4338CA] rounded-[4px]">
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
