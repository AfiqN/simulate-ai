import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import type { SimulationResult, RoundSummary, SchemaData } from "../types";

// ─── Colors ───────────────────────────────────────────────────────────────────
const COLORS = {
  primary: [26, 54, 93] as [number, number, number],
  secondary: [55, 65, 81] as [number, number, number],
  accent: [37, 99, 235] as [number, number, number],
  muted: [107, 114, 128] as [number, number, number],
  light: [243, 244, 246] as [number, number, number],
  white: [255, 255, 255] as [number, number, number],
  black: [15, 15, 15] as [number, number, number],
  verdictHigh: [22, 163, 74] as [number, number, number],
  verdictModerate: [202, 138, 4] as [number, number, number],
  verdictLow: [220, 38, 38] as [number, number, number],
};

// ─── Layout ───────────────────────────────────────────────────────────────────
const MARGIN = { left: 22, right: 22, top: 20, bottom: 20 };
const PAGE_WIDTH = 210;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN.left - MARGIN.right;
const PAGE_HEIGHT = 297;
const CONTENT_BOTTOM = PAGE_HEIGHT - MARGIN.bottom - 10;

// ─── Helper Class ─────────────────────────────────────────────────────────────
class PdfBuilder {
  pdf: jsPDF;
  y: number;
  pageNum: number;
  scenarioName: string;
  generatedDate: string;

  constructor(scenarioName: string) {
    this.pdf = new jsPDF("p", "mm", "a4");
    this.y = MARGIN.top;
    this.pageNum = 1;
    this.scenarioName = scenarioName;
    this.generatedDate = new Date().toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  checkPageBreak(needed: number) {
    if (this.y + needed > CONTENT_BOTTOM) {
      this.newPage();
    }
  }

  newPage() {
    this.addFooter();
    this.pdf.addPage();
    this.pageNum++;
    this.y = MARGIN.top;
    this.addHeader();
  }

  addHeader() {
    if (this.pageNum <= 1) return;
    this.pdf.setFont("helvetica", "normal");
    this.pdf.setFontSize(7);
    this.pdf.setTextColor(...COLORS.muted);

    const headerText = "SimulateAI — Executive Diagnostic Report";
    this.pdf.text(headerText, MARGIN.left, 12);

    // Truncate scenario name for header
    const maxScenarioWidth = 80;
    let scenarioHeader = this.scenarioName;
    while (this.pdf.getTextWidth(scenarioHeader) > maxScenarioWidth && scenarioHeader.length > 10) {
      scenarioHeader = scenarioHeader.slice(0, -4) + "…";
    }
    this.pdf.text(scenarioHeader, PAGE_WIDTH - MARGIN.right, 12, { align: "right" });

    // Thin separator line
    this.pdf.setDrawColor(220, 220, 220);
    this.pdf.setLineWidth(0.2);
    this.pdf.line(MARGIN.left, 14, PAGE_WIDTH - MARGIN.right, 14);
    this.y = 22;
  }

  addFooter() {
    const footerY = PAGE_HEIGHT - 10;
    this.pdf.setDrawColor(220, 220, 220);
    this.pdf.setLineWidth(0.2);
    this.pdf.line(MARGIN.left, footerY - 3, PAGE_WIDTH - MARGIN.right, footerY - 3);

    this.pdf.setFont("helvetica", "normal");
    this.pdf.setFontSize(7);
    this.pdf.setTextColor(...COLORS.muted);
    this.pdf.text(this.generatedDate, MARGIN.left, footerY);
    this.pdf.text("Confidential", PAGE_WIDTH / 2, footerY, { align: "center" });
    this.pdf.text(`${this.pageNum}`, PAGE_WIDTH - MARGIN.right, footerY, { align: "right" });
  }

  // ─── Text Renderers ───────────────────────────────────────────────────────

  addSectionTitle(text: string) {
    // Ensure at least 25mm of content space after the title
    this.checkPageBreak(25);
    this.y += 8;
    this.pdf.setFont("helvetica", "bold");
    this.pdf.setFontSize(12);
    this.pdf.setTextColor(...COLORS.primary);

    // Wrap title if too long
    const lines = this.pdf.splitTextToSize(text.toUpperCase(), CONTENT_WIDTH);
    for (const line of lines) {
      this.pdf.text(line, MARGIN.left, this.y);
      this.y += 5.5;
    }
    // Accent underline
    this.pdf.setDrawColor(...COLORS.accent);
    this.pdf.setLineWidth(0.6);
    this.pdf.line(MARGIN.left, this.y, MARGIN.left + 30, this.y);
    this.y += 6;
  }

  addSubsectionTitle(text: string) {
    // Ensure at least 20mm of content space after subsection header
    this.checkPageBreak(20);
    this.y += 5;
    this.pdf.setFont("helvetica", "bold");
    this.pdf.setFontSize(9.5);
    this.pdf.setTextColor(...COLORS.secondary);

    // Wrap long subsection titles
    const lines = this.pdf.splitTextToSize(text, CONTENT_WIDTH);
    for (const line of lines) {
      this.pdf.text(line, MARGIN.left, this.y);
      this.y += 4.5;
    }
    this.y += 2;
  }

  addParagraph(text: string, indent = 0) {
    this.pdf.setFont("helvetica", "normal");
    this.pdf.setFontSize(9);
    this.pdf.setTextColor(...COLORS.black);
    const maxWidth = CONTENT_WIDTH - indent;
    const lines = this.pdf.splitTextToSize(text, maxWidth);
    for (const line of lines) {
      this.checkPageBreak(4.5);
      this.pdf.text(line, MARGIN.left + indent, this.y);
      this.y += 4;
    }
    this.y += 2.5;
  }

  addBoldParagraph(text: string, indent = 0) {
    this.pdf.setFont("helvetica", "bold");
    this.pdf.setFontSize(9);
    this.pdf.setTextColor(...COLORS.black);
    const maxWidth = CONTENT_WIDTH - indent;
    const lines = this.pdf.splitTextToSize(text, maxWidth);
    for (const line of lines) {
      this.checkPageBreak(4.5);
      this.pdf.text(line, MARGIN.left + indent, this.y);
      this.y += 4;
    }
    this.y += 2;
  }

  addBullet(text: string, level = 0) {
    const indent = 4 + level * 5;
    const bulletChar = level === 0 ? "•" : "–";
    this.pdf.setFont("helvetica", "normal");
    this.pdf.setFontSize(9);
    this.pdf.setTextColor(...COLORS.black);
    const maxWidth = CONTENT_WIDTH - indent - 4;
    const lines = this.pdf.splitTextToSize(text, maxWidth);
    for (let i = 0; i < lines.length; i++) {
      this.checkPageBreak(4.5);
      if (i === 0) {
        this.pdf.text(bulletChar, MARGIN.left + indent, this.y);
      }
      this.pdf.text(lines[i], MARGIN.left + indent + 4, this.y);
      this.y += 4;
    }
    this.y += 1.5;
  }

  addSpace(mm: number) {
    this.y += mm;
  }

  addDivider() {
    this.y += 3;
    this.pdf.setDrawColor(230, 230, 230);
    this.pdf.setLineWidth(0.2);
    this.pdf.line(MARGIN.left, this.y, PAGE_WIDTH - MARGIN.right, this.y);
    this.y += 5;
  }

  addTable(headers: string[], rows: string[][]) {
    this.checkPageBreak(25);
    autoTable(this.pdf, {
      startY: this.y,
      head: [headers],
      body: rows,
      margin: { left: MARGIN.left, right: MARGIN.right },
      headStyles: {
        fillColor: COLORS.primary,
        textColor: COLORS.white,
        fontStyle: "bold",
        fontSize: 8,
        cellPadding: 2.5,
      },
      bodyStyles: {
        fontSize: 8,
        cellPadding: 2,
        textColor: COLORS.black,
      },
      alternateRowStyles: {
        fillColor: [249, 250, 251],
      },
      styles: {
        lineWidth: 0.1,
        lineColor: [230, 230, 230],
        overflow: "linebreak",
      },
      tableWidth: "auto",
    });
    this.y = (this.pdf as any).lastAutoTable.finalY + 8;
  }

  addKeyValue(label: string, value: string, valueColor?: [number, number, number]) {
    this.checkPageBreak(6);
    this.pdf.setFont("helvetica", "normal");
    this.pdf.setFontSize(8.5);
    this.pdf.setTextColor(...COLORS.muted);
    this.pdf.text(label + ":", MARGIN.left + 4, this.y);

    this.pdf.setFont("helvetica", "bold");
    this.pdf.setFontSize(8.5);
    this.pdf.setTextColor(...(valueColor || COLORS.black));
    this.pdf.text(value, MARGIN.left + 55, this.y);
    this.y += 5.5;
  }
}

// ─── Markdown Parser ──────────────────────────────────────────────────────────

interface MdSection {
  title: string;
  content: string;
}

function parseReportSections(reportMd: string): MdSection[] {
  const sections: MdSection[] = [];
  const parts = reportMd.split(/^## /m);
  for (const part of parts) {
    if (!part.trim()) continue;
    const firstNewline = part.indexOf("\n");
    if (firstNewline === -1) {
      sections.push({ title: cleanMarkdown(part.trim()), content: "" });
    } else {
      sections.push({
        title: cleanMarkdown(part.slice(0, firstNewline).trim()),
        content: part.slice(firstNewline + 1).trim(),
      });
    }
  }
  return sections;
}

function cleanMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/`(.*?)`/g, "$1")
    .replace(/^#+\s*/gm, "")
    .replace(/^>\s*/gm, "")
    .trim();
}

function renderMarkdownContent(builder: PdfBuilder, content: string) {
  const lines = content.split("\n");
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Subsection header (### )
    if (line.startsWith("### ")) {
      builder.addSubsectionTitle(cleanMarkdown(line.slice(4)));
      i++;
      continue;
    }

    // Sub-sub-section (#### ) — treat as bold paragraph
    if (line.startsWith("#### ")) {
      builder.addBoldParagraph(cleanMarkdown(line.slice(5)));
      i++;
      continue;
    }

    // Bullet line (handles various indentation)
    if (line.match(/^\s*[-•*]\s/)) {
      const indent = line.match(/^\s*/)?.[0].length || 0;
      const level = indent >= 4 ? 1 : 0;
      const text = cleanMarkdown(line.replace(/^\s*[-•*]\s+/, ""));
      if (text) builder.addBullet(text, level);
      i++;
      continue;
    }

    // Numbered list
    if (line.match(/^\s*\d+\.\s/)) {
      const text = cleanMarkdown(line.replace(/^\s*\d+\.\s+/, ""));
      if (text) builder.addBullet(text, 0);
      i++;
      continue;
    }

    // Block quote
    if (line.startsWith("> ")) {
      const text = cleanMarkdown(line.slice(2));
      if (text) builder.addParagraph(`"${text}"`, 4);
      i++;
      continue;
    }

    // Empty line
    if (!line.trim()) {
      builder.addSpace(1.5);
      i++;
      continue;
    }

    // Regular paragraph — accumulate contiguous lines
    let para = "";
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].startsWith("### ") &&
      !lines[i].startsWith("#### ") &&
      !lines[i].match(/^\s*[-•*]\s/) &&
      !lines[i].match(/^\s*\d+\.\s/) &&
      !lines[i].startsWith("> ") &&
      !lines[i].startsWith("## ")
    ) {
      para += (para ? " " : "") + lines[i].trim();
      i++;
    }
    if (para) {
      // Detect bold prefix like "**Label:** rest"
      const boldPrefixMatch = para.match(/^\*\*(.*?)\*\*:?\s*(.*)$/);
      if (boldPrefixMatch && boldPrefixMatch[2]) {
        builder.addBoldParagraph(cleanMarkdown(boldPrefixMatch[1]) + ":");
        builder.addParagraph(cleanMarkdown(boldPrefixMatch[2]), 2);
      } else if (para.startsWith("**") && para.endsWith("**")) {
        builder.addBoldParagraph(cleanMarkdown(para));
      } else {
        builder.addParagraph(cleanMarkdown(para));
      }
    }
  }
}

// ─── Cover Page ───────────────────────────────────────────────────────────────

function renderCoverPage(
  builder: PdfBuilder,
  result: SimulationResult,
  schema: SchemaData | null,
  rounds: RoundSummary[]
) {
  const pdf = builder.pdf;
  const scenarioName = schema?.scenario_name || result.scenario_name || "Simulation Report";
  const verdict = result.resilience_metrics?.verdict || result.verdict || "—";

  // Dark header band
  pdf.setFillColor(...COLORS.primary);
  pdf.rect(0, 0, PAGE_WIDTH, 80, "F");

  // Brand mark
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(9);
  pdf.setTextColor(180, 200, 230);
  pdf.text("SIMULATEAI", MARGIN.left, 25);

  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(8);
  pdf.setTextColor(150, 175, 210);
  pdf.text("Multi-Agent Behavioral Simulation", MARGIN.left, 31);

  // Scenario title
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(18);
  pdf.setTextColor(...COLORS.white);
  const titleLines = pdf.splitTextToSize(scenarioName, CONTENT_WIDTH - 10);
  let ty = 50;
  for (const line of titleLines) {
    pdf.text(line, MARGIN.left, ty);
    ty += 8;
  }

  // Report type subtitle
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.setTextColor(180, 200, 230);
  pdf.text("Executive Diagnostic Report", MARGIN.left, ty + 5);

  // ─── Below the band ─────────────────────────────────

  // Verdict section
  const verdictY = 100;
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(8);
  pdf.setTextColor(...COLORS.muted);
  pdf.text("RESILIENCE VERDICT", MARGIN.left, verdictY);

  const verdictColor = verdict === "Resilient" ? COLORS.verdictHigh
    : verdict === "Moderate" ? COLORS.verdictModerate
    : verdict === "Fragile" ? COLORS.verdictLow
    : COLORS.muted;

  pdf.setFillColor(...verdictColor);
  pdf.roundedRect(MARGIN.left, verdictY + 3, 42, 10, 1.5, 1.5, "F");
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(10);
  pdf.setTextColor(...COLORS.white);
  pdf.text(verdict.toUpperCase(), MARGIN.left + 21, verdictY + 10, { align: "center" });

  // ─── Key facts grid ─────────────────────────────────
  const gridY = 125;
  pdf.setDrawColor(230, 230, 230);
  pdf.setLineWidth(0.2);
  pdf.line(MARGIN.left, gridY - 5, PAGE_WIDTH - MARGIN.right, gridY - 5);

  const facts = [
    { label: "Date", value: builder.generatedDate },
    { label: "Agents", value: `${rounds[0]?.decisions?.length || "—"}` },
    { label: "Rounds", value: `${rounds.length}` },
    { label: "Duration", value: result.timings ? `${(result.timings.total / 60).toFixed(1)} minutes` : "—" },
    { label: "Decision Stability", value: result.resilience_metrics ? `${(result.resilience_metrics.decision_stability * 100).toFixed(0)}%` : "—" },
    { label: "Utility Drift", value: result.resilience_metrics ? `${result.resilience_metrics.utility_drift_mean >= 0 ? "+" : ""}${result.resilience_metrics.utility_drift_mean.toFixed(3)}` : "—" },
  ];

  let fy = gridY;
  for (const fact of facts) {
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(8.5);
    pdf.setTextColor(...COLORS.muted);
    pdf.text(fact.label, MARGIN.left + 2, fy);
    pdf.setFont("helvetica", "bold");
    pdf.setTextColor(...COLORS.black);
    pdf.text(fact.value, MARGIN.left + 50, fy);
    fy += 8;
  }

  // ─── Disclaimer ─────────────────────────────────────
  pdf.setFont("helvetica", "italic");
  pdf.setFontSize(7.5);
  pdf.setTextColor(...COLORS.muted);
  pdf.text(
    "This report was generated by SimulateAI multi-agent behavioral simulation platform.",
    MARGIN.left,
    PAGE_HEIGHT - 28
  );
  pdf.text(
    "Results are probabilistic and should inform — not replace — human judgment.",
    MARGIN.left,
    PAGE_HEIGHT - 23
  );

  // Confidential mark
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(7);
  pdf.text("CONFIDENTIAL", PAGE_WIDTH - MARGIN.right, PAGE_HEIGHT - 28, { align: "right" });

  builder.pageNum = 1;
}

// ─── Metrics Page ─────────────────────────────────────────────────────────────

function renderMetricsPage(builder: PdfBuilder, result: SimulationResult, rounds: RoundSummary[]) {
  builder.newPage();
  builder.addSectionTitle("Quantitative Metrics");

  // Key metrics summary
  if (result.resilience_metrics) {
    const rm = result.resilience_metrics;
    const verdictColor = rm.verdict === "Resilient" ? COLORS.verdictHigh
      : rm.verdict === "Moderate" ? COLORS.verdictModerate : COLORS.verdictLow;

    builder.addKeyValue("Resilience Verdict", rm.verdict, verdictColor);
    builder.addKeyValue("Decision Stability (R2→R3)", `${(rm.decision_stability * 100).toFixed(0)}%`);
    builder.addKeyValue("Mean Utility Drift", `${rm.utility_drift_mean >= 0 ? "+" : ""}${rm.utility_drift_mean.toFixed(3)}`);
    if (rm.rationale) {
      builder.addKeyValue("Rationale", rm.rationale);
    }
    builder.addDivider();
  }

  // Vote tally table
  if (rounds.length > 0) {
    builder.addSubsectionTitle("Vote Distribution by Round");
    const allActions = new Set<string>();
    rounds.forEach(r => Object.keys(r.vote_tally).forEach(a => allActions.add(a)));
    const actions = Array.from(allActions).sort();

    const headers = ["Round", ...actions];
    const rows = rounds.map(r => [
      `Round ${r.round}`,
      ...actions.map(a => `${r.vote_tally[a] || 0}`),
    ]);
    builder.addTable(headers, rows);
  }

  // Consensus index
  if (result.quantitative_metrics?.consensus_index) {
    builder.addSubsectionTitle("Consensus Index (HHI)");
    const ci = result.quantitative_metrics.consensus_index;
    const headers = ["Round", "HHI", "Interpretation"];
    const rows = Object.entries(ci).map(([round, value]) => [
      round.toUpperCase(),
      (value as number).toFixed(3),
      (value as number) >= 0.5 ? "Converging" : (value as number) >= 0.3 ? "Moderate" : "Fragmented",
    ]);
    builder.addTable(headers, rows);
  }

  // Dimension statistics
  if (result.quantitative_metrics?.dimension_stats) {
    builder.addSubsectionTitle("Evaluation Dimension Statistics");
    const stats = result.quantitative_metrics.dimension_stats;
    const headers = ["Dimension", "R1 Mean", "R2 Mean", "R3 Mean"];
    const rows: string[][] = [];
    for (const [dim, roundStats] of Object.entries(stats)) {
      const shortDim = dim.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      rows.push([
        shortDim,
        roundStats["r1"]?.mean?.toFixed(3) ?? "—",
        roundStats["r2"]?.mean?.toFixed(3) ?? "—",
        roundStats["r3"]?.mean?.toFixed(3) ?? "—",
      ]);
    }
    builder.addTable(headers, rows);
  }

  // Swing analysis
  if (result.quantitative_metrics?.swing_analysis) {
    const swings = result.quantitative_metrics.swing_analysis;
    const allSwings = Object.values(swings).flat();
    if (allSwings.length > 0) {
      builder.addSubsectionTitle("Position Changes (Swings)");
      const headers = ["Agent", "From", "To", "Driver Dimension", "Δ Utility"];
      const rows = allSwings.map(s => [
        s.archetype.replace(/_/g, " "),
        s.from_action,
        s.to_action,
        s.driver_dimension?.replace(/_/g, " ") || "—",
        s.utility_delta != null ? `${s.utility_delta >= 0 ? "+" : ""}${s.utility_delta.toFixed(3)}` : "—",
      ]);
      builder.addTable(headers, rows);
    }
  }
}

// ─── Main Export Function ─────────────────────────────────────────────────────

export function generateReport(
  result: SimulationResult,
  rounds: RoundSummary[],
  schema: SchemaData | null
) {
  const scenarioName = schema?.scenario_name || result.scenario_name || "Simulation Report";
  const builder = new PdfBuilder(scenarioName);

  // 1. Cover page
  renderCoverPage(builder, result, schema, rounds);

  // 2. Metrics page
  renderMetricsPage(builder, result, rounds);

  // 3. Report sections from report_md
  if (result.report_md) {
    const sections = parseReportSections(result.report_md);
    for (const section of sections) {
      builder.newPage();
      builder.addSectionTitle(section.title);
      renderMarkdownContent(builder, section.content);
    }
  }

  // Final footer on last page
  builder.addFooter();

  // Save
  const filename = `${scenarioName.replace(/[^a-zA-Z0-9]+/g, "_").toLowerCase()}_report.pdf`;
  builder.pdf.save(filename);
}
