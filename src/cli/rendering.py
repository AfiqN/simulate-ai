from rich.panel import Panel
from rich.table import Table

from src.agent.profile import AgentProfile
from src.cli import console
from src.schema.simulation_schema import SimulationSchema


def format_resources(profile: AgentProfile) -> str:
    if not profile.resources:
        return "—"
    return " | ".join(f"{r.name}: {r.current:,.0f}/{r.maximum:,.0f}" for r in profile.resources)


def ask_multiline(prompt_label: str) -> str:
    console.print(
        f"[bold green]{prompt_label}[/bold green] "
        f"[dim](Paste/type text, then press Ctrl+D on Linux/WSL or Ctrl+Z + Enter on Windows to submit)[/dim]:"
    )
    lines: list[str] = []
    while True:
        try:
            lines.append(input())
        except EOFError:
            break
    return "\n".join(lines).strip()


def render_schema_panel(schema: SimulationSchema) -> None:
    actions = ", ".join(a.name for a in schema.actions)
    clusters = ", ".join(c.cluster_id for c in schema.linguistic_clusters)
    if schema.resource_model.kind != "none" and schema.resource_model.resources:
        resource_summary = f"{schema.resource_model.kind} — " + ", ".join(
            r.name for r in schema.resource_model.resources
        )
    else:
        resource_summary = "none"

    body = (
        f"[bold]Scenario:[/bold] {schema.scenario_name}\n"
        f"[bold]Description:[/bold] {schema.scenario_description}\n"
        f"[bold]Verdict Label:[/bold] {schema.verdict_label}\n"
        f"[bold]Action Vocabulary:[/bold] {actions}\n"
        f"[bold]Linguistic Clusters:[/bold] {clusters}\n"
        f"[bold]Resource Model:[/bold] {resource_summary}\n"
        f"[bold]State Vocabulary:[/bold] {', '.join(schema.state_vocabulary)}\n"
        f"[bold]Crisis Dimensions:[/bold] {', '.join(schema.crisis_dimensions)}"
    )
    console.print(
        Panel(
            body,
            title="[bold yellow]Scenario Schema (Architect Output)[/bold yellow]",
            border_style="yellow",
        )
    )

    if schema.macro_context:
        console.print(
            Panel(
                schema.macro_context_text(),
                title="[bold yellow]Macro Environment Anchors[/bold yellow]",
                border_style="yellow",
            )
        )


def render_agent_table(profiles: list[AgentProfile], schema: SimulationSchema) -> None:
    table = Table(title=f"Swarm Members — {schema.scenario_name}", border_style="cyan")
    table.add_column("Agent ID", style="bold dim")
    table.add_column("Archetype", style="bold yellow")
    table.add_column("Cluster", style="blue")
    table.add_column("State", style="magenta")
    table.add_column("Attributes", style="cyan")
    table.add_column("Resources", style="green")

    for p in profiles:
        attr = p.attributes
        attr_str = (
            f"Rat: {attr.rationality_index:.2f} | "
            f"Agg: {attr.aggressiveness:.2f} | "
            f"Risk: {attr.risk_tolerance:.2f}"
        )
        table.add_row(
            p.agent_id,
            p.archetype.replace("_", " "),
            p.linguistic_cluster_id,
            p.current_internal_state,
            attr_str,
            format_resources(p),
        )
    console.print(table)


def make_parallel_status_table(statuses: list[dict], title: str = "Concurrent Execution Monitor") -> Table:
    table = Table(title=title, border_style="cyan")
    table.add_column("Agent ID", style="bold dim")
    table.add_column("Archetype", style="bold yellow")
    table.add_column("Status", style="bold")
    table.add_column("Time", style="green")

    for s in statuses:
        st = s["status"]
        if st == "Pending...":
            style = "[dim]Pending...[/dim]"
        elif st in ("Thinking...", "Debating...", "Reacting..."):
            style = f"[yellow]{st} ⏳[/yellow]"
        elif st == "Completed":
            style = "[green]✔ Completed[/green]"
        else:
            style = f"[red]❌ {st}[/red]"
        dur = f"{s['duration']:.2f}s" if s["duration"] > 0 else "---"
        table.add_row(s["id"], s["archetype"].replace("_", " "), style, dur)
    return table


def action_style(action: str, schema: SimulationSchema) -> str:
    action_def = next((a for a in schema.actions if a.name == action), None)
    if action_def is None:
        return "yellow"
    if action_def.is_terminal:
        return "red"
    if action_def.affects_resource:
        return "green"
    return "yellow"


def render_round_panel(round_label: str, decision: dict, schema: SimulationSchema, duration: float) -> None:
    style = action_style(decision["action"], schema)
    console.print(
        Panel(
            f"[italic dim]Internal Reflection:[/italic dim]\n"
            f"[dim]\"{decision['monologue']}\"[/dim]\n\n"
            f"[bold cyan]Public Statement:[/bold cyan]\n"
            f"\"{decision['statement']}\"\n\n"
            f"• Utility (U) : [bold]{decision['utility']:.4f}[/bold]\n"
            f"• Decision    : [{style}][bold]{decision['action']}[/bold][/{style}]\n"
            f"• State       : [magenta]{decision['new_state']}[/magenta]\n"
            f"• Latency     : [green]{duration:.2f}s[/green]",
            title=f"[bold yellow]{decision['archetype']} (ID: {decision['id']}) — {round_label}[/bold yellow]",
            border_style=style,
        )
    )
