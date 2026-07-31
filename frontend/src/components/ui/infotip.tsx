import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip";

interface Props {
  term: string;
  children: React.ReactNode;
}

/**
 * Inline info tooltip — wraps a term with a dotted underline and shows explanation on hover.
 */
export function InfoTip({ term, children }: Props) {
  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="border-b border-dotted border-[#B0B0B0] cursor-help">
            {term}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-[280px] leading-relaxed">
          {children}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
