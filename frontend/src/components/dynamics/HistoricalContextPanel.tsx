import { BookOpen, Calendar, ExternalLink } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { HistoricalPrecedent } from "../../types";

interface Props {
  precedents: HistoricalPrecedent[];
}

export function HistoricalContextPanel({ precedents }: Props) {
  if (!precedents || precedents.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Historical Precedents</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {precedents.map((p, i) => (
            <div
              key={`${p.title}-${i}`}
              className="p-3 rounded-[6px] border border-[#E5E5E5] animate-fade-in"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <BookOpen size={14} className="text-[#6B6B6B] flex-shrink-0 mt-0.5" />
                  <span className="text-[13px] font-medium text-[#0F0F0F]">{p.title}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {p.year && (
                    <Badge variant="outline" size="sm" className="gap-1">
                      <Calendar size={9} />
                      {p.year}
                    </Badge>
                  )}
                  {p.domain && (
                    <Badge variant="secondary" size="sm">
                      {p.domain}
                    </Badge>
                  )}
                </div>
              </div>

              {p.summary && (
                <p className="text-[12px] text-[#6B6B6B] mt-2 leading-relaxed pl-[22px]">
                  {p.summary}
                </p>
              )}

              {p.outcome && (
                <div className="mt-2 pl-[22px]">
                  <span className="text-[10px] text-[#9B9B9B] uppercase tracking-wider">Outcome</span>
                  <p className="text-[12px] text-[#0F0F0F] mt-0.5 leading-relaxed">{p.outcome}</p>
                </div>
              )}

              {p.relevance && (
                <div className="mt-2 pl-[22px] border-l-2 border-[#E5E5E5] ml-[22px] pl-3">
                  <p className="text-[11px] text-[#6B6B6B] italic">{p.relevance}</p>
                </div>
              )}

              {p.source && p.source !== "user-supplied" && (
                <div className="mt-2 pl-[22px]">
                  <a
                    href={p.source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] text-[#2563EB] hover:underline"
                  >
                    <ExternalLink size={10} />
                    Source
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
