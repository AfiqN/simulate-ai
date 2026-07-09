import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-[4px] border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default: "border-transparent bg-[#0F0F0F] text-white",
        secondary: "border-transparent bg-[#F5F5F5] text-[#6B6B6B]",
        success: "border-transparent bg-[#ECFDF5] text-[#16653A]",
        destructive: "border-transparent bg-[#FEF2F2] text-[#8B1A1A]",
        warning: "border-transparent bg-[#FFFBEB] text-[#6B5C1A]",
        shift: "border-transparent bg-[#EFF6FF] text-[#2563EB]",
        outline: "border-[#E5E5E5] text-[#6B6B6B]",
      },
      size: {
        sm: "px-1.5 py-0.5 text-[10px]",
        md: "px-2 py-0.5 text-[11px]",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
