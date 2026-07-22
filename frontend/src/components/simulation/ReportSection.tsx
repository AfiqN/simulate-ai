import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { SimulationResult } from "../../types";

interface Props {
  result: SimulationResult;
}

export function ReportSection({ result }: Props) {
  const [showRaw, setShowRaw] = useState(false);

  return (
    <div className="space-y-4">
      {/* Rendered markdown report */}
      {result.report_md && (
        <div className="prose prose-sm max-w-none text-[14px] leading-[1.7] text-[#0F0F0F] [&_h1]:text-[18px] [&_h1]:font-semibold [&_h1]:mt-6 [&_h1]:mb-3 [&_h1]:tracking-[-0.02em] [&_h2]:text-[15px] [&_h2]:font-medium [&_h2]:mt-5 [&_h2]:mb-2 [&_h3]:text-[14px] [&_h3]:font-medium [&_h3]:mt-4 [&_h3]:mb-1.5 [&_p]:mb-3 [&_ul]:pl-5 [&_ul]:mb-3 [&_ol]:pl-5 [&_ol]:mb-3 [&_li]:mb-1 [&_strong]:text-[#0F0F0F] [&_em]:text-[#6B6B6B] [&_blockquote]:border-l-2 [&_blockquote]:border-[#E5E5E5] [&_blockquote]:pl-4 [&_blockquote]:text-[#6B6B6B] [&_blockquote]:italic [&_code]:text-[12px] [&_code]:font-['JetBrains_Mono'] [&_code]:bg-[#F5F5F5] [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded-[3px]">
          <ReactMarkdown>{result.report_md}</ReactMarkdown>
        </div>
      )}

      {/* Collapsible raw JSON */}
      <div className="border-t border-[#F0F0F0] pt-3 mt-4">
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="flex items-center gap-1.5 text-[12px] text-[#9B9B9B] hover:text-[#6B6B6B] transition-colors"
        >
          <span className={`transition-transform duration-200 inline-block ${showRaw ? "rotate-90" : ""}`}>▸</span>
          Raw data
        </button>
        {showRaw && (
          <pre className="mt-3 p-4 bg-[#FAFAFA] border border-[#E5E5E5] rounded-[8px] text-[11px] font-['JetBrains_Mono'] text-[#6B6B6B] overflow-x-auto max-h-[400px] overflow-y-auto leading-relaxed">
            {JSON.stringify(result, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
