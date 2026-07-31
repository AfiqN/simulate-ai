import { useState } from "react";
import { Rocket, DollarSign, Globe, Building2, FileText, Bot, Trash2, TrendingUp, RefreshCw, Handshake } from "lucide-react";
import { useRevealOnScroll } from "../../hooks/useRevealOnScroll";

interface Template {
  id: string;
  icon: React.ReactNode;
  title: string;
  insight: string;
  stimulus: string;
  tags: string[];
  depth: "quick" | "standard" | "deep";
  agents: number;
  category: string;
}

const TEMPLATES: Template[] = [
  {
    id: "product-launch",
    icon: <Rocket size={20} strokeWidth={1.5} />,
    title: "Product Launch",
    insight: "Will users adopt? Who resists? What kills momentum?",
    stimulus: "We're launching a new SaaS product targeting mid-market companies. The product replaces a manual workflow with AI automation. Pricing is $49/seat/month. We're planning a Product Hunt launch followed by outbound sales. Key concern: our target buyers are conservative and skeptical of AI tools.",
    tags: ["Go-to-market", "Adoption"],
    depth: "standard",
    agents: 5,
    category: "Product",
  },
  {
    id: "pricing-change",
    icon: <DollarSign size={20} strokeWidth={1.5} />,
    title: "Pricing Strategy Change",
    insight: "How will customers and competitors react to a price shift?",
    stimulus: "We're considering raising prices by 40% for our B2B software product. Current plan: $29/user/month → $41/user/month. We have 2,000 paying customers. Competitors charge $25-$35. We believe our product delivers significantly more value but usage data shows only 60% of features are actively used.",
    tags: ["Revenue", "Churn Risk"],
    depth: "standard",
    agents: 5,
    category: "Business",
  },
  {
    id: "market-entry",
    icon: <Globe size={20} strokeWidth={1.5} />,
    title: "Market Entry",
    insight: "Is the market ready? What blocks entry? Who are allies?",
    stimulus: "A European fintech company wants to enter the Southeast Asian market, starting with Indonesia. The product is a digital lending platform for small businesses. Challenges include: regulatory complexity, incumbent banks, low digital literacy in target segment, and need for local partnerships.",
    tags: ["Expansion", "Regulatory"],
    depth: "deep",
    agents: 7,
    category: "Strategy",
  },
  {
    id: "hiring-decision",
    icon: <Building2 size={20} strokeWidth={1.5} />,
    title: "Hiring vs Outsourcing",
    insight: "Build in-house or outsource? What are the hidden costs?",
    stimulus: "Our 50-person startup needs to scale engineering capacity. We're deciding between hiring 10 full-time engineers (6-month ramp, $150K avg comp) versus outsourcing to a development agency ($80/hour, immediate start). Current team is burning out. Product roadmap has 6 months of committed features.",
    tags: ["Team", "Operations"],
    depth: "standard",
    agents: 5,
    category: "Operations",
  },
  {
    id: "policy-change",
    icon: <FileText size={20} strokeWidth={1.5} />,
    title: "Workplace Policy Change",
    insight: "How will employees and management respond?",
    stimulus: "A 500-person company is considering implementing a mandatory 4-day work week. Proposal: same pay, compressed hours (4x10h or reduced to 32h/week). The CEO believes it will improve retention and productivity. Middle management is skeptical about meeting deadlines. Some roles (customer support, sales) may not be compatible.",
    tags: ["HR", "Culture"],
    depth: "standard",
    agents: 5,
    category: "Operations",
  },
  {
    id: "ai-adoption",
    icon: <Bot size={20} strokeWidth={1.5} />,
    title: "AI Tool Adoption",
    insight: "Will the org embrace it or resist? What's the adoption curve?",
    stimulus: "A mid-size law firm (200 lawyers, 100 support staff) is evaluating whether to adopt an AI legal research and document drafting tool. The tool promises 60% time savings on routine work. Concerns: accuracy for high-stakes cases, partner buy-in, junior associate skill development, client perception, and bar association guidelines.",
    tags: ["AI", "Change Management"],
    depth: "deep",
    agents: 7,
    category: "Technology",
  },
  {
    id: "feature-kill",
    icon: <Trash2 size={20} strokeWidth={1.5} />,
    title: "Kill a Feature",
    insight: "Can we remove it? Who depends on it? What's the fallout?",
    stimulus: "We're considering removing our product's free tier entirely. Currently 80% of users are on free, 15% on pro ($19/mo), 5% on enterprise. Free users generate word-of-mouth but cost $3/user/month in infrastructure. Our investor wants us to focus on revenue. Some free users are potential enterprise leads.",
    tags: ["Product", "Revenue"],
    depth: "standard",
    agents: 5,
    category: "Product",
  },
  {
    id: "fundraising",
    icon: <TrendingUp size={20} strokeWidth={1.5} />,
    title: "Fundraising Pitch",
    insight: "Will investors bite? What objections will they raise?",
    stimulus: "A Series A startup (18 months old, $500K ARR, 40% MoM growth, $50K MRR) is pitching VCs for a $5M round at $25M pre-money. The product is an AI-powered customer success platform. The market is competitive (Gainsight, ChurnZero) but the AI angle is differentiated. Team is 12 people, mostly engineers. No VP Sales yet.",
    tags: ["Fundraising", "Investor"],
    depth: "deep",
    agents: 7,
    category: "Business",
  },
  {
    id: "org-restructure",
    icon: <RefreshCw size={20} strokeWidth={1.5} />,
    title: "Org Restructure",
    insight: "Who benefits, who loses? Will productivity survive the transition?",
    stimulus: "A 300-person company is restructuring from functional departments (Engineering, Design, Marketing, Sales) to cross-functional product squads. Each squad will own a specific product area end-to-end. Middle managers will lose direct reports. Some people will report to new leaders they've never worked with. Timeline: 3 months.",
    tags: ["Org Design", "Leadership"],
    depth: "standard",
    agents: 5,
    category: "Operations",
  },
  {
    id: "partnership",
    icon: <Handshake size={20} strokeWidth={1.5} />,
    title: "Strategic Partnership",
    insight: "Is this the right partner? What could go wrong?",
    stimulus: "A D2C skincare brand ($10M revenue, strong social presence) is considering an exclusive distribution partnership with a major retail chain (500+ stores). The deal: 3-year exclusive for physical retail, 30% margin to retailer, minimum order quantities. Risk: losing DTC margin, brand dilution, dependency on one channel.",
    tags: ["Partnership", "Growth"],
    depth: "standard",
    agents: 5,
    category: "Strategy",
  },
];

const CATEGORIES = ["All", "Product", "Business", "Strategy", "Operations", "Technology"];

function RevealCard({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const { ref, revealed } = useRevealOnScroll<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`reveal-on-scroll ${revealed ? "revealed" : ""}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

interface Props {
  onSelect: (stimulus: string, depth: "quick" | "standard" | "deep", agents: number) => void;
  onBack: () => void;
}

export function TemplateGallery({ onSelect, onBack }: Props) {
  const [filter, setFilter] = useState<string>("All");

  const filtered = filter === "All" ? TEMPLATES : TEMPLATES.filter((t) => t.category === filter);

  return (
    <div className="py-8 sm:py-12">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <button
            onClick={onBack}
            className="text-[13px] text-[#8B8B8B] hover:text-[#0F0F0F] transition-colors mb-2 block"
          >
            ← Back
          </button>
          <h1 className="text-[24px] sm:text-[32px] font-semibold tracking-[-0.03em] text-[#0F0F0F]">
            Templates
          </h1>
          <p className="text-[14px] text-[#6B6B6B] mt-1">
            Pick a scenario — or use it as a starting point for your own.
          </p>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 mb-8">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`px-3.5 py-1.5 text-[13px] rounded-[6px] transition-colors ${
              filter === cat
                ? "bg-[#0F0F0F] text-white"
                : "bg-[#F5F5F5] text-[#6B6B6B] hover:bg-[#EBEBEB] hover:text-[#0F0F0F]"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((template, i) => (
          <RevealCard key={template.id} delay={i * 50}>
            <button
              onClick={() => onSelect(template.stimulus, template.depth, template.agents)}
              className="group w-full text-left border border-[#E5E5E5] rounded-[12px] p-5 hover:border-[#0F0F0F]/20 hover:shadow-[0_4px_16px_rgba(0,0,0,0.06)] transition-all duration-200 h-full flex flex-col"
            >
              <div className="w-[36px] h-[36px] rounded-[8px] bg-[#F5F5F5] flex items-center justify-center text-[#6B6B6B] mb-3">{template.icon}</div>
              <h3 className="text-[15px] font-medium text-[#0F0F0F] mb-1.5 group-hover:text-[#0F0F0F]">
                {template.title}
              </h3>
              <p className="text-[13px] text-[#6B6B6B] leading-[1.5] mb-4 flex-1">
                {template.insight}
              </p>
              <div className="flex items-center justify-between">
                <div className="flex gap-1.5">
                  {template.tags.map((tag) => (
                    <span key={tag} className="text-[10px] text-[#8B8B8B] bg-[#F5F5F5] px-1.5 py-0.5 rounded">
                      {tag}
                    </span>
                  ))}
                </div>
                <span className="text-[10px] text-[#B0B0B0] font-['JetBrains_Mono']">
                  {template.agents}a · {template.depth}
                </span>
              </div>
            </button>
          </RevealCard>
        ))}
      </div>
    </div>
  );
}
