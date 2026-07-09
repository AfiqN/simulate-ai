import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
    <Card className="border-[#D97706]/30 bg-[#FFFBEB] p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-[#D97706] uppercase tracking-wider font-medium">Schema Pending Approval</span>
          <span className="text-[11px] text-[#9B9B9B]">Auto-approves in 120s</span>
        </div>
        <Button onClick={handleApprove} disabled={approving} size="sm">
          {approving ? "Approving..." : "Approve & Continue"}
        </Button>
      </div>

      <div className="space-y-3">
        <div>
          <h3 className="text-[14px] font-medium text-[#0F0F0F]">{schema.scenario_name}</h3>
        </div>

        <div>
          <span className="text-[11px] text-[#6B6B6B] uppercase tracking-wider">Actions</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {schema.actions.map((a) => (
              <Badge
                key={a.name}
                variant={a.is_terminal ? "destructive" : "secondary"}
                className={a.is_terminal ? "bg-[#8B1A1A]/10" : ""}
              >
                {a.name}{a.is_terminal ? " ⊘" : ""}
              </Badge>
            ))}
          </div>
        </div>

        <div>
          <span className="text-[11px] text-[#6B6B6B] uppercase tracking-wider">Evaluation Dimensions</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {schema.evaluation_dimensions.map((dim) => (
              <Badge key={dim} variant="secondary">{dim}</Badge>
            ))}
          </div>
        </div>

        {schema.state_vocabulary && schema.state_vocabulary.length > 0 && (
          <div>
            <span className="text-[11px] text-[#6B6B6B] uppercase tracking-wider">State Vocabulary</span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {schema.state_vocabulary.map((s) => (
                <Badge key={s} variant="outline" className="bg-[#EEF2FF] text-[#4338CA] border-transparent">
                  {s}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}
