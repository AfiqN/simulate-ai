interface Props {
  label: string;
  variant?: "positive" | "negative" | "neutral" | "shift" | "default";
  size?: "sm" | "md";
}

export function Badge({ label, variant = "default", size = "md" }: Props) {
  const colors = {
    positive: "bg-[#ECFDF5] text-[#16653A]",
    negative: "bg-[#FEF2F2] text-[#8B1A1A]",
    neutral: "bg-[#FEFCE8] text-[#6B5C1A]",
    shift: "bg-[#EFF6FF] text-[#2563EB]",
    default: "bg-[#F5F5F5] text-[#6B6B6B]",
  };

  const sizes = {
    sm: "px-1.5 py-0.5 text-[10px]",
    md: "px-2 py-0.5 text-[11px]",
  };

  return (
    <span className={`inline-block rounded-[4px] font-medium uppercase tracking-wider ${colors[variant]} ${sizes[size]}`}>
      {label}
    </span>
  );
}
