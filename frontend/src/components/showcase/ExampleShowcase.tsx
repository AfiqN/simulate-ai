import { useState } from "react";
import { transformMetrics } from "../../lib/transformMetrics";
import type { ExampleData } from "../../lib/transformMetrics";

interface ExampleMeta {
  id: string;
  file: string;
  title: string;
  subtitle: string;
  agents: number;
  verdict: string;
  tags: string[];
}

const EXAMPLES: ExampleMeta[] = [
  {
    id: "ai-workforce",
    file: "/examples/ai-workforce-displacement.json",
    title: "AI Workforce Displacement in Fintech",
    subtitle: "Should a fintech replace 40% of support staff with AI chatbots?",
    agents: 10,
    verdict: "Resilient",
    tags: ["Corporate Strategy", "Labor Relations", "Regulatory Risk"],
  },
  {
    id: "edutwin",
    file: "/examples/edutwin-university-adoption.json",
    title: "EduTwin AI — University Adoption",
    subtitle: "Will Indonesian universities adopt an AI-powered digital twin for student learning?",
    agents: 5,
    verdict: "Resilient",
    tags: ["EdTech", "Data Privacy", "Institutional Decision"],
  },
  {
    id: "smart-factory",
    file: "/examples/smart-factory-defect-detection.json",
    title: "Smart Factory Defect Detection",
    subtitle: "Can a hackathon team's multi-camera defect detection system survive judge scrutiny?",
    agents: 5,
    verdict: "Resilient",
    tags: ["Hackathon", "Computer Vision", "Technical Feasibility"],
  },
];

function VerdictBadge({ verdict }: { verdict: string }) {
  const colors: Record<string, string> = {
    Resilient: "bg-[#ECFDF5] text-[#065F46]",
    Moderate: "bg-[#FFF7ED] text-[#9A3412]",
    Fragile: "bg-[#FEF2F2] text-[#991B1B]",
  };
  return (
    <span className={`px-2 py-0.5 text-[11px] font-medium rounded-[4px] ${colors[verdict] || "bg-[#F3F4F6] text-[#374151]"}`}>
      {verdict}
    </span>
  );
}

interface Props {
  onLoadExample: (data: ExampleData) => void;
}

export function ExampleShowcase({ onLoadExample }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  async function handleClick(example: ExampleMeta) {
    setLoading(example.id);
    try {
      const res = await fetch(example.file);
      if (!res.ok) throw new Error(`Failed to load example`);
      const raw = await res.json();
      const data = transformMetrics(raw);
      onLoadExample(data);
    } catch (err) {
      console.error("Failed to load example:", err);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-[13px] text-[#8B8B8B] tracking-wide uppercase">
          Example Simulations
        </h2>
        <span className="text-[11px] text-[#B0B0B0] font-['JetBrains_Mono']">
          click to explore results
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {EXAMPLES.map((ex) => (
          <button
            key={ex.id}
            onClick={() => handleClick(ex)}
            disabled={loading !== null}
            className="group text-left w-full border border-[#E5E5E5] rounded-[10px] p-5 hover:border-[#0F0F0F]/20 hover:shadow-[0_2px_8px_rgba(0,0,0,0.04)] transition-all duration-150 disabled:opacity-60"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-medium text-[#0F0F0F] group-hover:text-[#0F0F0F] truncate">
                  {loading === ex.id ? "Loading..." : ex.title}
                </p>
                <p className="text-[13px] text-[#6B6B6B] mt-0.5 line-clamp-1">
                  {ex.subtitle}
                </p>
                <div className="flex items-center gap-2 mt-2.5">
                  <span className="text-[11px] text-[#8B8B8B] font-['JetBrains_Mono']">
                    {ex.agents} agents · 3 rounds
                  </span>
                  <span className="text-[#E0E0E0]">·</span>
                  <div className="flex gap-1.5">
                    {ex.tags.map((tag) => (
                      <span key={tag} className="text-[10px] text-[#8B8B8B] bg-[#F5F5F5] px-1.5 py-0.5 rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <VerdictBadge verdict={ex.verdict} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
