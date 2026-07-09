import { Zap, AlertTriangle, Users, TrendingDown, ArrowRightLeft } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { TriggersEvent } from "../../types";

const EFFECT_CONFIG: Record<string, { icon: typeof Zap; color: string; bg: string; label: string }> = {
  inject_event: { icon: Zap, color: "#D97706", bg: "#FFFBEB", label: "Event Injected" },
  notify: { icon: AlertTriangle, color: "#6B6B6B", bg: "#F5F5F5", label: "Notification" },
  modify_agents: { icon: Users, color: "#2563EB", bg: "#EFF6FF", label: "Agents Modified" },
  escalate_crisis: { icon: TrendingDown, color: "#8B1A1A", bg: "#FEF2F2", label: "Crisis Escalated" },
  add_round: { icon: ArrowRightLeft, color: "#7C3AED", bg: "#F5F3FF", label: "Round Added" },
};

interface Props {
  triggers: TriggersEvent[];
}

export function ConditionalTriggersPanel({ triggers }: Props) {
  if (!triggers || triggers.length === 0) return null;

  const allFired = triggers.flatMap((t) =>
    t.triggers.map((tr) => ({ ...tr, round: t.round }))
  );

  if (allFired.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Conditional Triggers</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {allFired.map((t, i) => {
            const config = EFFECT_CONFIG[t.effect] || EFFECT_CONFIG.notify;
            const Icon = config.icon;

            return (
              <div
                key={`${t.rule}-${t.round}-${i}`}
                className="flex items-start gap-3 p-3 rounded-[6px] border border-[#E5E5E5] animate-fade-in"
              >
                <div
                  className="flex-shrink-0 w-7 h-7 rounded-[4px] flex items-center justify-center mt-0.5"
                  style={{ backgroundColor: config.bg }}
                >
                  <Icon size={14} style={{ color: config.color }} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-medium text-[#0F0F0F]">{t.rule}</span>
                    <Badge variant="secondary" size="sm">R{t.round}</Badge>
                  </div>

                  <div className="mt-1 flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className="text-[10px]"
                      style={{ color: config.color, borderColor: `${config.color}30` }}
                    >
                      {config.label}
                    </Badge>
                    {t.context.ratio && (
                      <span className="text-[11px] text-[#9B9B9B] font-['JetBrains_Mono'] tabular-nums">
                        {(t.context.ratio * 100).toFixed(0)}%
                      </span>
                    )}
                    {t.context.action && (
                      <span className="text-[11px] text-[#6B6B6B]">{t.context.action}</span>
                    )}
                    {t.context.swing_count && (
                      <span className="text-[11px] text-[#6B6B6B]">{t.context.swing_count} agents shifted</span>
                    )}
                    {t.context.drop_pct && (
                      <span className="text-[11px] text-[#8B1A1A] font-['JetBrains_Mono'] tabular-nums">
                        −{(t.context.drop_pct * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
