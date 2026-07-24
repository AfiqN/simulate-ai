import { useEffect, useRef } from "react";

const DEFAULT_TITLE = "SimulateAI — Stress-test decisions with multi-agent AI simulation";

/**
 * Updates the document title to reflect simulation progress.
 * Reverts to default title on unmount or when status is idle.
 */
export function useDocumentTitle(status: string, progress: number) {
  const revertTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (revertTimerRef.current) {
      clearTimeout(revertTimerRef.current);
      revertTimerRef.current = null;
    }

    switch (status) {
      case "running":
      case "schema_pending":
        document.title = `⏳ ${Math.round(progress)}% — SimulateAI`;
        break;
      case "complete":
        document.title = "✅ Done — SimulateAI";
        revertTimerRef.current = setTimeout(() => {
          document.title = DEFAULT_TITLE;
        }, 8000);
        break;
      case "error":
        document.title = "❌ Failed — SimulateAI";
        revertTimerRef.current = setTimeout(() => {
          document.title = DEFAULT_TITLE;
        }, 8000);
        break;
      default:
        document.title = DEFAULT_TITLE;
    }

    return () => {
      if (revertTimerRef.current) clearTimeout(revertTimerRef.current);
    };
  }, [status, progress]);

  // Revert on focus if complete/error
  useEffect(() => {
    function handleFocus() {
      if (status === "complete" || status === "error") {
        document.title = DEFAULT_TITLE;
      }
    }
    window.addEventListener("focus", handleFocus);
    return () => window.removeEventListener("focus", handleFocus);
  }, [status]);
}
