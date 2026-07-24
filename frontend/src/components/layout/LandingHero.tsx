import { useRevealOnScroll } from "../../hooks/useRevealOnScroll";

interface Props {
  onGetStarted: () => void;
}

function RevealSection({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const { ref, revealed } = useRevealOnScroll<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`reveal-on-scroll ${revealed ? "revealed" : ""} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

function NodeGraph() {
  return (
    <div className="relative w-full h-[140px] sm:h-[180px] flex items-center justify-center select-none" aria-hidden="true">
      <svg viewBox="0 0 480 160" className="w-full max-w-[480px] h-full" fill="none">
        {/* Input to agents - static lines */}
        <line x1="60" y1="80" x2="180" y2="40" stroke="#E0E0E0" strokeWidth="1" />
        <line x1="60" y1="80" x2="180" y2="80" stroke="#E0E0E0" strokeWidth="1" />
        <line x1="60" y1="80" x2="180" y2="120" stroke="#E0E0E0" strokeWidth="1" />

        {/* Agents to verdict - static lines */}
        <line x1="300" y1="40" x2="420" y2="80" stroke="#E0E0E0" strokeWidth="1" />
        <line x1="300" y1="80" x2="420" y2="80" stroke="#E0E0E0" strokeWidth="1" />
        <line x1="300" y1="120" x2="420" y2="80" stroke="#E0E0E0" strokeWidth="1" />

        {/* Debate lines between agents - fully connected 3×3 animated dashes */}
        <line x1="180" y1="40" x2="300" y2="40" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="40" x2="300" y2="80" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "0.3s" }} className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="40" x2="300" y2="120" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "0.6s" }} className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="80" x2="300" y2="40" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "0.9s" }} className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="80" x2="300" y2="80" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "1.2s" }} className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="80" x2="300" y2="120" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "1.5s" }} className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="120" x2="300" y2="40" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "1.8s" }} className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="120" x2="300" y2="80" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "2.1s" }} className="animate-[dash_2.5s_linear_infinite]" />
        <line x1="180" y1="120" x2="300" y2="120" stroke="#0F0F0F" strokeWidth="1.2" strokeDasharray="3 6" style={{ animationDelay: "2.4s" }} className="animate-[dash_2.5s_linear_infinite]" />

        {/* Input node */}
        <circle cx="60" cy="80" r="7" fill="#0F0F0F" />
        <text x="60" y="104" textAnchor="middle" fill="#8B8B8B" fontSize="9" fontFamily="JetBrains Mono">STIMULUS</text>

        {/* Agent nodes - left column */}
        <circle cx="180" cy="40" r="5.5" fill="#0F0F0F" />
        <circle cx="180" cy="80" r="5.5" fill="#0F0F0F" />
        <circle cx="180" cy="120" r="5.5" fill="#0F0F0F" />

        {/* Agent nodes - right column (debate partners) */}
        <circle cx="300" cy="40" r="5.5" fill="#0F0F0F" />
        <circle cx="300" cy="80" r="5.5" fill="#0F0F0F" />
        <circle cx="300" cy="120" r="5.5" fill="#0F0F0F" />

        {/* Agent group labels */}
        <text x="240" y="14" textAnchor="middle" fill="#8B8B8B" fontSize="9" fontFamily="JetBrains Mono">DEBATE</text>

        {/* Verdict node */}
        <circle cx="420" cy="80" r="7" fill="#0F0F0F" />
        <text x="420" y="104" textAnchor="middle" fill="#8B8B8B" fontSize="9" fontFamily="JetBrains Mono">VERDICT</text>

        {/* Bracket hints for agent groups */}
        <text x="180" y="145" textAnchor="middle" fill="#C0C0C0" fontSize="8" fontFamily="JetBrains Mono">round 1</text>
        <text x="300" y="145" textAnchor="middle" fill="#C0C0C0" fontSize="8" fontFamily="JetBrains Mono">round 2</text>
      </svg>
    </div>
  );
}

export function LandingHero({ onGetStarted }: Props) {
  return (
    <div className="py-12 sm:py-20">
      {/* Hero */}
      <section className="text-center max-w-[640px] mx-auto mb-16 sm:mb-20">
        <p className="text-[13px] text-[#8B8B8B] tracking-wide mb-4 animate-reveal" style={{ animationDelay: "0ms" }}>
          For founders, PMs, and strategists
        </p>
        <h1
          className="text-[28px] sm:text-[40px] md:text-[48px] font-semibold tracking-[-0.035em] text-[#0F0F0F] leading-[1.1] mb-5 animate-reveal"
          style={{ animationDelay: "80ms" }}
        >
          Know what will go wrong
          <span className="block text-[#8B8B8B]">before it does</span>
        </h1>
        <p
          className="text-[15px] sm:text-[17px] text-[#6B6B6B] leading-[1.6] max-w-[480px] mx-auto mb-8 animate-reveal"
          style={{ animationDelay: "160ms" }}
        >
          AI personas debate your idea from every angle — surfacing blind spots,
          coalition risks, and failure modes in minutes.
        </p>
        <div className="animate-reveal" style={{ animationDelay: "240ms" }}>
          <button
            onClick={onGetStarted}
            className="group px-7 py-3 text-[15px] font-medium bg-[#0F0F0F] text-white rounded-[8px] hover:bg-[#2A2A2A] transition-all duration-150 hover:shadow-[0_4px_12px_rgba(0,0,0,0.15)]"
          >
            Run a simulation
            <span className="inline-block ml-1.5 transition-transform duration-150 group-hover:translate-x-0.5">→</span>
          </button>
        </div>

        {/* Node graph visual */}
        <div className="mt-10 animate-reveal" style={{ animationDelay: "320ms" }}>
          <NodeGraph />
        </div>
      </section>

      {/* How it works - with visual structure */}
      <RevealSection className="max-w-[860px] mx-auto mb-16 sm:mb-20">
        <div className="bg-[#FAFAFA] rounded-[16px] p-6 sm:p-10">
          <h2 className="text-[13px] text-[#8B8B8B] tracking-wide uppercase mb-8">
            How it works
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-0">
            {[
              {
                step: "01",
                title: "Describe a decision",
                body: "A product launch, policy change, strategic bet — anything with stakeholders and uncertainty.",
              },
              {
                step: "02",
                title: "Agents stress-test it",
                body: "LLM-generated personas form coalitions, debate, and react to a crisis event across three rounds.",
              },
              {
                step: "03",
                title: "Get a diagnostic",
                body: "Verdict, resilience score, risk map, and actionable recommendations — ready to share.",
              },
            ].map((item, i) => (
              <div
                key={item.step}
                className={`p-5 space-y-2.5 ${i < 2 ? "sm:border-r sm:border-[#E5E5E5]" : ""}`}
              >
                <div className="flex items-center gap-2">
                  <span className="w-[22px] h-[22px] rounded-full bg-[#0F0F0F] text-white text-[10px] font-['JetBrains_Mono'] flex items-center justify-center">
                    {item.step}
                  </span>
                  <h3 className="text-[14px] font-medium text-[#0F0F0F] tracking-[-0.01em]">
                    {item.title}
                  </h3>
                </div>
                <p className="text-[13px] text-[#6B6B6B] leading-[1.6] pl-[30px]">
                  {item.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* Output preview */}
      <RevealSection className="max-w-[860px] mx-auto mb-16 sm:mb-20">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[13px] text-[#8B8B8B] tracking-wide uppercase">
            What you get
          </h2>
          <span className="text-[11px] text-[#B0B0B0] font-['JetBrains_Mono']">sample output</span>
        </div>
        <div className="border border-[#E5E5E5] rounded-[12px] bg-white overflow-hidden shadow-[0_2px_8px_rgba(0,0,0,0.04)]">
          {/* Top bar */}
          <div className="border-b border-[#F0F0F0] px-6 py-3 flex items-center gap-1.5">
            <div className="w-[8px] h-[8px] rounded-full bg-[#E5E5E5]" />
            <div className="w-[8px] h-[8px] rounded-full bg-[#E5E5E5]" />
            <div className="w-[8px] h-[8px] rounded-full bg-[#E5E5E5]" />
          </div>
          <div className="p-6 sm:p-8 space-y-5">
            <div className="flex items-start sm:items-center justify-between gap-3 flex-col sm:flex-row">
              <div>
                <p className="text-[15px] font-medium text-[#0F0F0F]">Launch a 4-day work week at a 500-person company</p>
                <p className="text-[12px] text-[#8B8B8B] mt-0.5">5 agents · 3 rounds · collaborative mode</p>
              </div>
              <span className="px-2.5 py-1 text-[11px] font-medium bg-[#F3F0FF] text-[#5B21B6] rounded-[5px] whitespace-nowrap">
                Conditionally Viable
              </span>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Resilience", value: "72%" },
                { label: "Consensus", value: "3 / 5" },
                { label: "Risk level", value: "Moderate" },
              ].map((m) => (
                <div key={m.label} className="text-center py-3 border border-[#F0F0F0] rounded-[6px]">
                  <p className="text-[16px] sm:text-[18px] font-semibold text-[#0F0F0F] font-['JetBrains_Mono']">{m.value}</p>
                  <p className="text-[11px] text-[#8B8B8B] mt-0.5">{m.label}</p>
                </div>
              ))}
            </div>
            <div className="flex gap-1.5">
              {["Perception", "Debate", "Crisis"].map((round, i) => (
                <div key={round} className="flex-1">
                  <div className={`h-[6px] rounded-[3px] ${i === 2 ? "bg-[#F0F0F0]" : "bg-[#0F0F0F]"}`} />
                  <p className="text-[10px] text-[#8B8B8B] mt-1 font-['JetBrains_Mono']">{round}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </RevealSection>

      {/* Dark section - use cases */}
      <RevealSection className="mb-16 sm:mb-20">
        <div className="bg-[#0F0F0F] rounded-[16px] max-w-[860px] mx-auto p-6 sm:p-10">
          <h2 className="text-[13px] text-[#6B6B6B] tracking-wide uppercase mb-8">
            Use cases
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                title: "Product launches",
                desc: "Will users adopt? Which stakeholders will resist? What kills momentum?",
              },
              {
                title: "Policy decisions",
                desc: "Test political feasibility, coalition stability, and unintended consequences.",
              },
              {
                title: "Strategic bets",
                desc: "Stress-test M&A, market entry, org restructures — before committing resources.",
              },
            ].map((uc) => (
              <div key={uc.title} className="p-5 rounded-[10px] bg-[#1A1A1A] border border-[#2A2A2A] space-y-2">
                <h3 className="text-[14px] font-medium text-white">{uc.title}</h3>
                <p className="text-[13px] text-[#8B8B8B] leading-[1.6]">{uc.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </RevealSection>

      {/* Bottom CTA */}
      <RevealSection className="text-center max-w-[480px] mx-auto mb-12">
        <h2 className="text-[20px] sm:text-[24px] font-semibold tracking-[-0.02em] text-[#0F0F0F] mb-3">
          Decisions are expensive. Simulations aren't.
        </h2>
        <p className="text-[14px] text-[#6B6B6B] mb-6">
          Free to use — bring your own API key for unlimited runs.
        </p>
        <button
          onClick={onGetStarted}
          className="group px-7 py-3 text-[15px] font-medium bg-[#0F0F0F] text-white rounded-[8px] hover:bg-[#2A2A2A] transition-all duration-150 hover:shadow-[0_4px_12px_rgba(0,0,0,0.15)]"
        >
          Try it now
          <span className="inline-block ml-1.5 transition-transform duration-150 group-hover:translate-x-0.5">→</span>
        </button>
      </RevealSection>

      {/* Footer */}
      <footer className="border-t border-[#F0F0F0] pt-6 max-w-[860px] mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-[12px] text-[#8B8B8B]">
          <div className="flex items-center gap-2">
            <div className="w-[14px] h-[14px] bg-[#0F0F0F] rounded-[3px]" />
            <span className="font-medium text-[#6B6B6B]">SimulateAI</span>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="https://github.com/afiq2001/SimulateAI"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-[#0F0F0F] transition-colors"
            >
              GitHub
            </a>
            <span className="text-[#E0E0E0]">·</span>
            <span>Open-source simulation engine</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
