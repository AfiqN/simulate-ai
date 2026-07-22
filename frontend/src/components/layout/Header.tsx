interface Props {
  onOpenSettings: () => void;
}

export function Header({ onOpenSettings }: Props) {
  return (
    <header className="border-b border-[#E5E5E5] px-6 py-4 flex items-center justify-between">
      <h1 className="text-[20px] font-medium tracking-[-0.02em]">SimulateAI</h1>
      <button
        onClick={onOpenSettings}
        className="px-3 py-1.5 text-[13px] rounded-[6px] border border-[#E5E5E5] text-[#6B6B6B] hover:border-[#D0D0D0] hover:text-[#0F0F0F] transition-colors"
      >
        Settings
      </button>
    </header>
  );
}
