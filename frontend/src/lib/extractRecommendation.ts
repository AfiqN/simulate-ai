/**
 * Extract the key recommendation from a simulation report markdown.
 * Looks for "RECOMMENDATION" heading and takes the first meaningful sentence.
 */
export function extractRecommendation(reportMd: string | undefined): string | null {
  if (!reportMd) return null;

  // Try to find recommendation section
  const patterns = [
    /#+\s*(?:\d+\.?\s*)?(?:STRATEGIC\s+)?(?:PIVOT\s+)?RECOMMENDATION[S]?\s*\n+([\s\S]*?)(?=\n#+|\n---|$)/i,
    /#+\s*(?:\d+\.?\s*)?ONE\s+RECOMMENDATION\s*\n+([\s\S]*?)(?=\n#+|\n---|$)/i,
    /\*\*Recommendation[s]?\*\*[:\s]*([\s\S]*?)(?=\n\n|\n#+)/i,
  ];

  for (const pattern of patterns) {
    const match = reportMd.match(pattern);
    if (match && match[1]) {
      // Clean up: remove markdown formatting, take first sentence or meaningful chunk
      let text = match[1]
        .replace(/\*\*\d+\.\s*/g, "") // remove **1.
        .replace(/\*\*/g, "") // remove bold
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // links to text
        .replace(/^[-*]\s+/gm, "") // list markers
        .trim();

      // Take first sentence (up to period + space, or first 150 chars)
      const firstSentence = text.match(/^(.+?[.!])\s/);
      if (firstSentence && firstSentence[1].length > 20) {
        text = firstSentence[1];
      } else {
        // Take first line
        text = text.split("\n")[0].trim();
      }

      // Cap at reasonable length
      if (text.length > 140) {
        text = text.slice(0, 137) + "...";
      }

      if (text.length > 15) return text;
    }
  }

  return null;
}
