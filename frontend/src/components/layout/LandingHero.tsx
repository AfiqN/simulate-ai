interface Props {
  onGetStarted: () => void;
}

export function LandingHero({ onGetStarted }: Props) {
  return (
    <div className="py-16 space-y-10">
      {/* Hero */}
      <div className="text-center space-y-4">
        <h2 className="text-[32px] font-semibold tracking-[-0.03em] text-[#0F0F0F]">
          Stress-test any decision before it happens
        </h2>
        <p className="text-[16px] text-[#6B6B6B] max-w-[560px] mx-auto leading-relaxed">
          SimulateAI runs a multi-agent debate on your idea — product launch, policy change,
          strategic bet — and surfaces risks, consensus gaps, and resilience before reality does.
        </p>
      </div>

      {/* How it works */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-[720px] mx-auto">
        <div className="border border-[#E5E5E5] rounded-[8px] p-5 space-y-2">
          <div className="text-[13px] font-medium text-[#9B9B9B] uppercase tracking-wider">1</div>
          <h3 className="text-[14px] font-medium text-[#0F0F0F]">Describe your scenario</h3>
          <p className="text-[13px] text-[#6B6B6B] leading-relaxed">
            A product pitch, policy proposal, strategic decision — anything with stakeholders and uncertainty.
          </p>
        </div>
        <div className="border border-[#E5E5E5] rounded-[8px] p-5 space-y-2">
          <div className="text-[13px] font-medium text-[#9B9B9B] uppercase tracking-wider">2</div>
          <h3 className="text-[14px] font-medium text-[#0F0F0F]">Agents debate & stress-test</h3>
          <p className="text-[13px] text-[#6B6B6B] leading-relaxed">
            AI-generated personas evaluate across 3 rounds: perception, adversarial debate, and crisis shock.
          </p>
        </div>
        <div className="border border-[#E5E5E5] rounded-[8px] p-5 space-y-2">
          <div className="text-[13px] font-medium text-[#9B9B9B] uppercase tracking-wider">3</div>
          <h3 className="text-[14px] font-medium text-[#0F0F0F]">Get a diagnostic report</h3>
          <p className="text-[13px] text-[#6B6B6B] leading-relaxed">
            Verdict, risk map, resilience score, and actionable recommendations — in minutes.
          </p>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center">
        <button
          onClick={onGetStarted}
          className="px-6 py-2.5 text-[14px] font-medium bg-[#1A1A1A] text-white rounded-[8px] hover:bg-[#333] transition-colors"
        >
          Run a Simulation
        </button>
      </div>

      {/* Example prompts */}
      <div className="max-w-[560px] mx-auto">
        <p className="text-[12px] text-[#9B9B9B] uppercase tracking-wider font-medium mb-3 text-center">
          Example scenarios
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          {[
            "Launch a 4-day work week policy at a 500-person company",
            "Release an AI code assistant as a paid SaaS product",
            "Propose a carbon tax in a developing economy",
          ].map((ex) => (
            <span
              key={ex}
              className="px-3 py-1.5 text-[12px] text-[#6B6B6B] bg-[#F5F5F5] rounded-[6px] leading-snug"
            >
              {ex}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
