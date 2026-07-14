"""Report generator for validation/hindsight testing results."""

import os
from datetime import datetime
from typing import Optional

from tests.validation.models import CaseResult, ValidationReport


def _grade_color(grade: str) -> str:
    """Rich color for grade display."""
    return {
        "Strong": "bold green",
        "Moderate": "bold yellow",
        "Weak": "bold red",
        "Fail": "bold white on red",
    }.get(grade, "bold white")


def _score_bar(score: float, width: int = 10) -> str:
    """Simple text bar for score visualization (ASCII-safe)."""
    filled = round(score / 10 * width)
    return "#" * filled + "-" * (width - filled)


def generate_report_markdown(report: ValidationReport) -> str:
    """Generate the accuracy_report.md content."""
    lines = [
        "# SimulateAI Validation Report — Hindsight Testing",
        "",
        f"**Generated:** {report.timestamp}",
        f"**Model:** `{report.model_used}`",
        f"**Runs per case:** {report.runs_per_case}",
        "",
        "---",
        "",
        "## Overall Results",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Overall Score | **{report.overall_score:.2f}** / 10 |",
        f"| Grade | **{report.grade}** |",
        f"| Cases Evaluated | {len(report.cases)} |",
        f"| Successful Runs | {sum(len(c.runs) for c in report.cases)} / {len(report.cases) * report.runs_per_case} |",
        "",
        "### Grading Scale",
        "",
        "| Grade | Threshold |",
        "|-------|-----------|",
        "| Strong | >= 7.5 |",
        "| Moderate | >= 5.5 |",
        "| Weak | >= 3.5 |",
        "| Fail | < 3.5 |",
        "",
        "---",
        "",
        "## Per-Case Breakdown",
        "",
        "| Case | Domain | Median Score | Verdict | Behavior | Risks | Resilience |",
        "|------|--------|-------------|---------|----------|-------|------------|",
    ]

    for case in report.cases:
        dims = case.median_dimensions
        if case.simulation_error:
            lines.append(
                f"| {case.case_name} | {case.domain} | ERROR | - | - | - | - |"
            )
        elif not case.runs:
            lines.append(
                f"| {case.case_name} | {case.domain} | N/A | - | - | - | - |"
            )
        else:
            lines.append(
                f"| {case.case_name} | {case.domain} | "
                f"**{case.median_score:.1f}** | "
                f"{dims.get('verdict_match', 0):.1f} | "
                f"{dims.get('behavioral_fidelity', 0):.1f} | "
                f"{dims.get('risk_identification', 0):.1f} | "
                f"{dims.get('resilience_accuracy', 0):.1f} |"
            )

    lines.extend([
        "",
        "---",
        "",
        "## Per-Domain Breakdown",
        "",
        "| Domain | Avg Score | Cases |",
        "|--------|-----------|-------|",
    ])

    domain_counts: dict[str, int] = {}
    for case in report.cases:
        domain_counts[case.domain] = domain_counts.get(case.domain, 0) + 1

    for domain, avg in sorted(report.per_domain.items(), key=lambda x: -x[1]):
        lines.append(f"| {domain} | {avg:.2f} | {domain_counts.get(domain, 0)} |")

    lines.extend([
        "",
        "---",
        "",
        "## Dimension Weights",
        "",
        "| Dimension | Weight | Description |",
        "|-----------|--------|-------------|",
        "| verdict_match | 0.30 | Does simulation conclusion match reality? |",
        "| behavioral_fidelity | 0.25 | Do agent behaviors match real-world actors? |",
        "| risk_identification | 0.25 | Were actual risks identified? |",
        "| resilience_accuracy | 0.20 | Was Fragile/Moderate/Resilient correct? |",
        "",
    ])

    return "\n".join(lines)


def write_report(report: ValidationReport, output_dir: str) -> str:
    """Write the report to accuracy_report.md and return the file path."""
    md_content = generate_report_markdown(report)
    output_path = os.path.join(output_dir, "accuracy_report.md")
    os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    return output_path


def print_console_summary(report: ValidationReport) -> None:
    """Print a rich console summary of results."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
    except ImportError:
        # Fallback plain text
        print(f"\n=== Validation Report ===")
        print(f"Overall: {report.overall_score:.2f}/10 — Grade: {report.grade}")
        for case in report.cases:
            print(f"  {case.case_name}: {case.median_score:.1f}/10")
        return

    console = Console()

    # Header panel
    console.print()
    console.print(Panel(
        f"[bold]Overall Score:[/bold] {report.overall_score:.2f} / 10\n"
        f"[bold]Grade:[/bold] [{_grade_color(report.grade)}]{report.grade}[/{_grade_color(report.grade)}]\n"
        f"[bold]Model:[/bold] {report.model_used}\n"
        f"[bold]Runs per case:[/bold] {report.runs_per_case}",
        title="[bold cyan]SimulateAI Hindsight Validation[/bold cyan]",
        border_style="cyan",
    ))

    # Per-case table
    table = Table(title="Per-Case Results", border_style="dim")
    table.add_column("Case", style="bold")
    table.add_column("Domain", style="dim")
    table.add_column("Score", justify="right")
    table.add_column("Bar", no_wrap=True)
    table.add_column("Verdict", justify="right")
    table.add_column("Behavior", justify="right")
    table.add_column("Risks", justify="right")
    table.add_column("Resilience", justify="right")

    for case in report.cases:
        if case.simulation_error or not case.runs:
            table.add_row(
                case.case_name, case.domain,
                "[red]ERR[/red]", "", "-", "-", "-", "-"
            )
            continue
        dims = case.median_dimensions
        score = case.median_score
        score_color = "green" if score >= 7.5 else "yellow" if score >= 5.5 else "red"
        table.add_row(
            case.case_name,
            case.domain,
            f"[{score_color}]{score:.1f}[/{score_color}]",
            _score_bar(score),
            f"{dims.get('verdict_match', 0):.1f}",
            f"{dims.get('behavioral_fidelity', 0):.1f}",
            f"{dims.get('risk_identification', 0):.1f}",
            f"{dims.get('resilience_accuracy', 0):.1f}",
        )

    console.print(table)

    # Domain breakdown
    if report.per_domain:
        domain_table = Table(title="Per-Domain Averages", border_style="dim")
        domain_table.add_column("Domain", style="bold")
        domain_table.add_column("Avg Score", justify="right")
        for domain, avg in sorted(report.per_domain.items(), key=lambda x: -x[1]):
            color = "green" if avg >= 7.5 else "yellow" if avg >= 5.5 else "red"
            domain_table.add_row(domain, f"[{color}]{avg:.2f}[/{color}]")
        console.print(domain_table)

    console.print()
