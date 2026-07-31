interface Props {
  onOpenSettings: () => void;
  onLogoClick?: () => void;
  onHistoryClick?: () => void;
}

export function Header({ onOpenSettings, onLogoClick, onHistoryClick }: Props) {
  return (
    <header className="px-6 py-4 flex items-center justify-between max-w-[960px] mx-auto">
      <button
        onClick={onLogoClick}
        className="flex items-center gap-2.5 hover:opacity-70 transition-opacity"
      >
        <img src="/logo-mark.svg" alt="" className="h-[22px] w-auto" />
        <span className="text-[15px] font-medium tracking-[-0.01em] text-[#0F0F0F]">
          SimulateAI
        </span>
      </button>
      <div className="flex items-center gap-4">
        <button
          onClick={onHistoryClick}
          className="text-[13px] text-[#8B8B8B] hover:text-[#0F0F0F] transition-colors duration-150"
        >
          History
        </button>
        <button
          onClick={onOpenSettings}
          className="text-[13px] text-[#8B8B8B] hover:text-[#0F0F0F] transition-colors duration-150"
        >
          Settings
        </button>
      </div>
    </header>
  );
}
