interface Props {
  onOpenSettings: () => void;
}

export function Header({ onOpenSettings }: Props) {
  return (
    <header className="px-6 py-4 flex items-center justify-between max-w-[960px] mx-auto">
      <div className="flex items-center gap-2">
        <div className="w-[18px] h-[18px] bg-[#0F0F0F] rounded-[4px]" />
        <span className="text-[15px] font-medium tracking-[-0.01em] text-[#0F0F0F]">
          SimulateAI
        </span>
      </div>
      <button
        onClick={onOpenSettings}
        className="px-3 py-1.5 text-[13px] rounded-[6px] text-[#8B8B8B] hover:text-[#0F0F0F] transition-colors duration-150"
      >
        Settings
      </button>
    </header>
  );
}
