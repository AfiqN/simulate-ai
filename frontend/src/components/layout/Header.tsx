interface Props {
  showHistory: boolean;
  showWebhooks: boolean;
  onToggleHistory: () => void;
  onToggleWebhooks: () => void;
}

export function Header({ showHistory, showWebhooks, onToggleHistory, onToggleWebhooks }: Props) {
  return (
    <header className="border-b border-[#E5E5E5] px-6 py-4 flex items-center justify-between">
      <h1 className="text-[20px] font-medium tracking-[-0.02em]">SimulateAI</h1>
      <div className="flex items-center gap-2">
        <button
          onClick={onToggleWebhooks}
          className={`px-3 py-1.5 text-[13px] rounded-[6px] border transition-colors ${
            showWebhooks
              ? "border-[#1A1A1A] bg-[#1A1A1A] text-white"
              : "border-[#E5E5E5] text-[#6B6B6B] hover:border-[#D0D0D0] hover:text-[#0F0F0F]"
          }`}
        >
          Webhooks
        </button>
        <button
          onClick={onToggleHistory}
          className={`px-3 py-1.5 text-[13px] rounded-[6px] border transition-colors ${
            showHistory
              ? "border-[#1A1A1A] bg-[#1A1A1A] text-white"
              : "border-[#E5E5E5] text-[#6B6B6B] hover:border-[#D0D0D0] hover:text-[#0F0F0F]"
          }`}
        >
          History
        </button>
      </div>
    </header>
  );
}
