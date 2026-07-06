import { AlertTriangle, ShieldCheck } from "lucide-react";

interface Props {
  stressEvent: string;
  validationEvent?: string | null;
}

export function CrisisCallout({ stressEvent, validationEvent }: Props) {
  return (
    <div className="space-y-3">
      {/* Stress event */}
      <div className="relative border border-[#8B1A1A]/30 rounded-[8px] bg-gradient-to-r from-[#FEF2F2] to-white overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#8B1A1A]" />
        <div className="p-5 pl-6">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-[#8B1A1A]" />
            <span className="text-[12px] text-[#8B1A1A] uppercase tracking-wider font-semibold">
              Crisis Event
            </span>
          </div>
          <p className="text-[14px] text-[#0F0F0F] leading-relaxed">{stressEvent}</p>
        </div>
      </div>

      {/* Validation event (if any) */}
      {validationEvent && (
        <div className="relative border border-[#166534]/30 rounded-[8px] bg-gradient-to-r from-[#F0FDF4] to-white overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-1 bg-[#166534]" />
          <div className="p-5 pl-6">
            <div className="flex items-center gap-2 mb-2">
              <ShieldCheck size={16} className="text-[#166534]" />
              <span className="text-[12px] text-[#166534] uppercase tracking-wider font-semibold">
                Validation Event
              </span>
            </div>
            <p className="text-[14px] text-[#0F0F0F] leading-relaxed">{validationEvent}</p>
          </div>
        </div>
      )}
    </div>
  );
}
