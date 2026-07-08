import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DefectionEvent } from "@/types";

interface Props {
  events: DefectionEvent[];
}

export function DefectionLog({ events }: Props) {
  if (!events || events.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Defection Events</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="max-h-[220px] overflow-y-auto space-y-2 pr-1">
          {events.map((ev, i) => (
            <div
              key={i}
              className="flex items-center gap-2 py-1.5 px-2 rounded-md bg-[#FAFAFA] border border-[#F0F0F0]"
            >
              {/* Round badge */}
              <Badge variant="outline" className="shrink-0 font-mono text-[10px]">
                R{ev.round}
              </Badge>

              {/* Agent name */}
              <span className="text-[12px] font-medium text-[#0F0F0F] truncate">
                {ev.agent}
              </span>

              {/* Flow arrow */}
              <span className="flex items-center gap-1 ml-auto shrink-0">
                <Badge variant="destructive" className="text-[10px]">
                  {ev.from}
                </Badge>
                <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true">
                  <path
                    d="M1 5h10m0 0L8.5 2.5M11 5L8.5 7.5"
                    stroke="#9B9B9B"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <Badge variant="success" className="text-[10px]">
                  {ev.to}
                </Badge>
              </span>
            </div>
          ))}
        </div>
        <p className="text-[11px] text-[#9B9B9B] mt-2">
          {events.length} defection{events.length !== 1 ? "s" : ""} recorded
        </p>
      </CardContent>
    </Card>
  );
}
