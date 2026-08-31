import { useState } from "react";
import type { SimulationResult } from "../../types";
import { askRun, getRunToken } from "../../lib/api";

interface Props {
  result: SimulationResult;
  runId?: string;
}

export function AskPanel({ result, runId }: Props) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questionsAsked, setQuestionsAsked] = useState(0);

  const MAX_QUESTIONS = 5;

  const handleAsk = async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    setAnswer(null);

    try {
      if (!runId || !getRunToken(runId)) {
        throw new Error("Follow-up questions are available only to the run owner.");
      }
      const answer = await askRun(runId, question.trim(), result.report_md || "");
      setAnswer(answer);
      setQuestionsAsked((n) => n + 1);
    } catch (err: any) {
      setError(err.message || "Failed to get answer");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const atLimit = questionsAsked >= MAX_QUESTIONS;

  return (
    <div className="border border-[#E5E5E5] rounded-[10px] bg-white overflow-hidden">
      <div className="px-5 py-4 border-b border-[#F0F0F0]">
        <h3 className="text-[14px] font-medium text-[#0F0F0F]">Ask about this simulation</h3>
        <p className="text-[12px] text-[#8B8B8B] mt-0.5">
          Ask follow-up questions based on the analysis report.
        </p>
      </div>

      <div className="p-5 space-y-4">
        {/* Answer display */}
        {answer && (
          <div className="p-4 bg-[#FAFAFA] rounded-[8px] border border-[#F0F0F0]">
            <p className="text-[13px] text-[#0F0F0F] leading-[1.6] whitespace-pre-wrap">{answer}</p>
          </div>
        )}

        {error && (
          <div className="p-3 bg-[#FEF2F2] border border-[#8B1A1A]/20 rounded-[6px]">
            <p className="text-[12px] text-[#8B1A1A]">{error}</p>
          </div>
        )}

        {/* Input */}
        {!atLimit ? (
          <div className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              placeholder="e.g. Which agent is most likely to flip if budget doubles?"
              className="flex-1 px-3.5 py-2.5 text-[13px] text-[#0F0F0F] placeholder:text-[#B0B0B0] border border-[#E5E5E5] rounded-[8px] focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-colors disabled:opacity-50"
            />
            <button
              onClick={handleAsk}
              disabled={loading || !question.trim()}
              className="px-4 py-2.5 text-[13px] font-medium bg-[#0F0F0F] text-white rounded-[8px] hover:bg-[#2A2A2A] transition-colors disabled:opacity-40 shrink-0"
            >
              {loading ? "Thinking..." : "Ask"}
            </button>
          </div>
        ) : (
          <p className="text-[12px] text-[#8B8B8B] text-center py-2">
            Question limit reached for this session. Run a new simulation to ask more.
          </p>
        )}

        {questionsAsked > 0 && !atLimit && (
          <p className="text-[11px] text-[#B0B0B0] text-right">
            {questionsAsked}/{MAX_QUESTIONS} questions used
          </p>
        )}
      </div>
    </div>
  );
}
