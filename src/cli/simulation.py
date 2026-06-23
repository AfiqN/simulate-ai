import asyncio
import time
from typing import Any, Optional

from rich.live import Live
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table

from config import DEFAULT_MODEL, LLM_PROVIDER, OLLAMA_HOST
from src.agent.adversary import compute_adversary_map
from src.agent.agent import Agent
from src.agent.swarm import SwarmGenerationError, generate_llm_swarm
from src.cli import console
from src.cli.rendering import (
    action_style,
    ask_multiline,
    format_resources,
    make_parallel_status_table,
    render_agent_table,
    render_round_panel,
    render_schema_panel,
)
from src.llm.client import OllamaClient
from src.report.compiler import ExecutiveCompiler, Valence, compute_resilience_metrics
from src.schema.architect import SchemaDesignError, design_schema
from src.schema.simulation_schema import SimulationSchema


async def check_llm_provider(client: OllamaClient) -> bool:
    host_display = "Google AI Studio" if LLM_PROVIDER == "gemini" else OLLAMA_HOST
    console.print(f"[dim]Connecting to {host_display}...[/dim]", end=" ")
    available = await client.is_available()
    if not available:
        console.print("[red]FAILED[/red]")
        if LLM_PROVIDER == "gemini":
            console.print(
                "[red]Error:[/red] Failed to authenticate with the Gemini API.\n"
                "Check your API key in config.py."
            )
        else:
            console.print(
                f"[red]Error:[/red] Ollama is not reachable at [yellow]{OLLAMA_HOST}[/yellow].\n"
                "Start it with: [bold]ollama serve[/bold]"
            )
        return False
    console.print("[green]OK[/green]")
    return True


async def _run_perception(
    idx: int,
    agent: Agent,
    stimulus: str,
    statuses: list[dict],
    semaphore: asyncio.Semaphore,
) -> None:
    await asyncio.sleep(idx * 2)
    await _execute_round(
        idx,
        statuses,
        semaphore,
        in_progress_label="Thinking...",
        coroutine_factory=lambda: agent.perceive_and_react(stimulus),
    )


async def _run_debate(
    idx: int,
    agent: Agent,
    stimulus: str,
    round1_transcript: str,
    adversary: Optional[dict],
    statuses: list[dict],
    semaphore: asyncio.Semaphore,
) -> None:
    await asyncio.sleep(4 + idx * 3)
    await _execute_round(
        idx,
        statuses,
        semaphore,
        in_progress_label="Debating...",
        coroutine_factory=lambda: agent.debate_and_react(
            stimulus, round1_transcript, adversary=adversary if adversary else None
        ),
    )


async def _run_crisis(
    idx: int,
    agent: Agent,
    crisis: str,
    original_stimulus: str,
    statuses: list[dict],
    semaphore: asyncio.Semaphore,
) -> None:
    await asyncio.sleep(4 + idx * 3)
    await _execute_round(
        idx,
        statuses,
        semaphore,
        in_progress_label="Reacting...",
        coroutine_factory=lambda: agent.react_to_crisis(crisis, original_stimulus),
    )


async def _execute_round(
    idx: int,
    statuses: list[dict],
    semaphore: asyncio.Semaphore,
    in_progress_label: str,
    coroutine_factory,
) -> None:
    start = time.time()
    statuses[idx]["status"] = in_progress_label
    try:
        async with semaphore:
            result = await coroutine_factory()
        statuses[idx]["duration"] = time.time() - start
        statuses[idx]["status"] = "Failed" if "error" in result else "Completed"
        statuses[idx]["result"] = result
    except Exception as e:
        statuses[idx]["duration"] = time.time() - start
        statuses[idx]["status"] = "Failed"
        statuses[idx]["result"] = {"error": str(e)}


def _make_statuses(agents: list[Agent]) -> list[dict]:
    return [
        {
            "id": a.profile.agent_id,
            "archetype": a.profile.archetype,
            "status": "Pending...",
            "duration": 0.0,
            "result": {},
        }
        for a in agents
    ]


def _extract_decision(agent: Agent, status_entry: dict, schema: SimulationSchema) -> dict:
    archetype_title = agent.profile.archetype.replace("_", " ")
    result = status_entry["result"]
    fallback_action = schema.actions[0].name if schema.actions else "ABSTAIN"

    if "error" in result or not result:
        return {
            "id": agent.profile.agent_id,
            "archetype": archetype_title,
            "action": fallback_action,
            "utility": 0.0,
            "monologue": f"Error: {result.get('error', 'no response')}",
            "statement": "(no response)",
            "new_state": agent.profile.current_internal_state,
            "duration": status_entry["duration"],
        }
    return {
        "id": agent.profile.agent_id,
        "archetype": archetype_title,
        "action": result.get("action_decision", fallback_action),
        "utility": result.get("utility", 0.0),
        "monologue": result.get("internal_reflection", "..."),
        "statement": result.get("public_statement", "..."),
        "new_state": result.get("new_internal_state", agent.profile.current_internal_state),
        "duration": status_entry["duration"],
    }


async def _drive_live_table(statuses: list[dict], title: str, in_progress_labels: set[str]) -> None:
    with Live(make_parallel_status_table(statuses, title), refresh_per_second=5) as live:
        while any(s["status"] in in_progress_labels or s["status"] == "Pending..." for s in statuses):
            await asyncio.sleep(0.2)
            live.update(make_parallel_status_table(statuses, title))
        live.update(make_parallel_status_table(statuses, title))


def _pick_valence(stimulus: str) -> Valence:
    return "validation" if hash(stimulus) % 2 == 0 else "stress"


def _render_final_summary(
    schema: SimulationSchema,
    agents: list[Agent],
    decisions_r1: list[dict],
    decisions_r2: list[dict],
    decisions_r3: list[dict],
    dur_r1: float,
    dur_r2: float,
    dur_r3: float,
) -> None:
    console.print(Rule("[bold magenta]SIMULATION CONCLUDED[/bold magenta]"))
    console.print(
        f"• Round 1 Time : [green]{dur_r1:.2f}s[/green]\n"
        f"• Round 2 Time : [green]{dur_r2:.2f}s[/green]\n"
        f"• Round 3 Time : [green]{dur_r3:.2f}s[/green]\n"
        f"• Total        : [yellow]{dur_r1 + dur_r2 + dur_r3:.2f}s[/yellow] "
        f"for [yellow]{len(agents)}[/yellow] agents across 3 rounds.\n"
    )

    r1_lookup = {d["id"]: d for d in decisions_r1}
    r2_lookup = {d["id"]: d for d in decisions_r2}

    res_table = Table(title="3-Round Verdict Comparison", border_style="magenta")
    res_table.add_column("Archetype", style="bold yellow")
    res_table.add_column("R1", style="bold")
    res_table.add_column("R2", style="bold")
    res_table.add_column("R3", style="bold")
    res_table.add_column("Final State", style="magenta")
    res_table.add_column("Resources", style="green")

    def tag(action: str) -> str:
        style = action_style(action, schema)
        return f"[{style}]{action}[/{style}]"

    for d in decisions_r3:
        aid = d["id"]
        r1 = r1_lookup.get(aid, {})
        r2 = r2_lookup.get(aid, {})
        profile = next(a.profile for a in agents if a.profile.agent_id == aid)
        res_table.add_row(
            d["archetype"],
            tag(r1.get("action", "?")),
            tag(r2.get("action", "?")),
            tag(d["action"]),
            d["new_state"],
            format_resources(profile),
        )

    console.print(res_table)


async def run_simulation_pipeline(
    client: OllamaClient,
    stimulus: str,
    agent_count: int,
    concurrency: int,
) -> dict[str, Any]:
    with Live(
        Spinner("aesthetic", text="[bold yellow]Architect is designing the simulation schema...[/bold yellow]"),
        refresh_per_second=10,
    ) as live:
        schema = await design_schema(client, stimulus)
        live.update("[bold green]✔ Schema designed.[/bold green]")

    render_schema_panel(schema)

    console.print()
    with Live(
        Spinner("aesthetic", text="[bold yellow]Generating agent personas...[/bold yellow]"),
        refresh_per_second=10,
    ) as live:
        profiles = await generate_llm_swarm(client, schema, stimulus, agent_count)
        live.update("[bold green]✔ Personas generated.[/bold green]")

    agents = [Agent(profile, client, schema) for profile in profiles]
    render_agent_table(profiles, schema)

    semaphore = asyncio.Semaphore(concurrency)

    console.print()
    console.print(Rule("[bold cyan]ROUND 1 — INITIAL PERCEPTION[/bold cyan]"))
    statuses_r1 = _make_statuses(agents)
    t0 = time.time()
    tasks_r1 = [
        asyncio.create_task(_run_perception(i, a, stimulus, statuses_r1, semaphore))
        for i, a in enumerate(agents)
    ]
    await _drive_live_table(statuses_r1, "Round 1 Monitor", {"Thinking..."})
    await asyncio.gather(*tasks_r1)
    dur_r1 = time.time() - t0

    decisions_r1: list[dict] = []
    transcript_parts_r1: list[str] = []
    for i, a in enumerate(agents):
        d = _extract_decision(a, statuses_r1[i], schema)
        decisions_r1.append(d)
        render_round_panel("Round 1 — Initial Perception", d, schema, statuses_r1[i]["duration"])
        transcript_parts_r1.append(
            f"Agent: {d['archetype']} (ID: {d['id']})\n"
            f"- Public Statement: \"{d['statement']}\"\n"
            f"- Action Committed: {d['action']}"
        )
    full_round1_transcript = "\n\n".join(transcript_parts_r1)

    console.print()
    adversary_map = compute_adversary_map(decisions_r1, agents)
    console.print(
        Panel(
            "\n".join(
                f"[bold yellow]{decisions_r1[i]['archetype']}[/bold yellow] → challenges → "
                f"[bold red]"
                f"{adversary_map[decisions_r1[i]['id']]['archetype'] if adversary_map[decisions_r1[i]['id']] else 'no adversary (homogeneous swarm)'}"
                f"[/bold red]"
                for i in range(len(agents))
            ),
            title="[bold cyan]Directed Interaction Graph (ΔU Pairing)[/bold cyan]",
            border_style="cyan",
        )
    )

    console.print()
    console.print(Rule("[bold magenta]ROUND 2 — DIRECTED DEBATE[/bold magenta]"))
    statuses_r2 = _make_statuses(agents)
    t0 = time.time()
    tasks_r2 = [
        asyncio.create_task(_run_debate(
            i, a, stimulus, full_round1_transcript,
            adversary_map.get(a.profile.agent_id),
            statuses_r2, semaphore,
        ))
        for i, a in enumerate(agents)
    ]
    await _drive_live_table(statuses_r2, "Round 2 Debate Monitor", {"Thinking...", "Debating..."})
    await asyncio.gather(*tasks_r2)
    dur_r2 = time.time() - t0

    decisions_r2: list[dict] = []
    for i, a in enumerate(agents):
        d = _extract_decision(a, statuses_r2[i], schema)
        decisions_r2.append(d)
        render_round_panel("Round 2 — Directed Debate", d, schema, statuses_r2[i]["duration"])

    console.print()
    console.print(Rule("[bold red]ROUND 3 — CRISIS STRESS-TEST[/bold red]"))
    transcript_parts_r2 = [
        f"Agent: {d['archetype']} (ID: {d['id']})\n"
        f"- Public Statement: \"{d['statement']}\"\n"
        f"- Action: {d['action']}"
        for d in decisions_r2
    ]
    full_round2_transcript = "\n\n".join(transcript_parts_r2)

    await asyncio.sleep(2)
    compiler = ExecutiveCompiler(client, schema)
    valence: Valence = _pick_valence(stimulus)
    with Live(
        Spinner("aesthetic", text=f"[bold red]Catalyst Agent synthesizing {valence} event...[/bold red]"),
        refresh_per_second=10,
    ) as live:
        crisis_event = await compiler.generate_crisis_event(
            stimulus, full_round2_transcript, valence=valence,
        )
        live.update(f"[bold red]⚡ {valence.title()} Event Injected[/bold red]")

    panel_color = "green" if valence == "validation" else "red"
    panel_label = "Validation Shock" if valence == "validation" else "Crisis"
    console.print()
    console.print(
        Panel(
            f"[bold {panel_color}]{crisis_event}[/bold {panel_color}]",
            title=f"[bold]⚡ External {panel_label} Event — Injected by System[/bold]",
            border_style=panel_color,
        )
    )

    statuses_r3 = _make_statuses(agents)
    t0 = time.time()
    tasks_r3 = [
        asyncio.create_task(_run_crisis(i, a, crisis_event, stimulus, statuses_r3, semaphore))
        for i, a in enumerate(agents)
    ]
    await _drive_live_table(statuses_r3, "Round 3 Crisis Monitor", {"Reacting..."})
    await asyncio.gather(*tasks_r3)
    dur_r3 = time.time() - t0

    decisions_r3: list[dict] = []
    for i, a in enumerate(agents):
        d = _extract_decision(a, statuses_r3[i], schema)
        decisions_r3.append(d)
        render_round_panel("Round 3 — Crisis Reaction", d, schema, statuses_r3[i]["duration"])

    console.print()
    console.print(Rule("[bold yellow]COMPILING EXECUTIVE DIAGNOSTIC REPORT[/bold yellow]"))
    resilience_metrics = compute_resilience_metrics(decisions_r2, decisions_r3, schema)
    console.print(
        Panel(
            f"[bold]Verdict:[/bold] {resilience_metrics['verdict']}\n"
            f"[dim]{resilience_metrics['rationale']}[/dim]",
            title="[bold yellow]Deterministic Resilience Metrics[/bold yellow]",
            border_style="yellow",
        )
    )
    await asyncio.sleep(2)
    with Live(
        Spinner("aesthetic", text="[bold yellow]Chief Behavioral Architect analyzing transcripts...[/bold yellow]"),
        refresh_per_second=10,
    ) as live:
        report_md = await compiler.compile_report(
            stimulus, decisions_r1, decisions_r2,
            round3_results=decisions_r3, crisis_event=crisis_event,
            resilience_metrics=resilience_metrics,
        )
        live.update("[bold green]✔ Report compiled[/bold green]")

    console.print()
    console.print(
        Panel(
            report_md,
            title=f"[bold yellow]SIMULATEAI EXECUTIVE DIAGNOSTIC REPORT — {schema.scenario_name}[/bold yellow]",
            border_style="yellow",
            expand=True,
        )
    )

    _render_final_summary(schema, agents, decisions_r1, decisions_r2, decisions_r3, dur_r1, dur_r2, dur_r3)

    return {
        "schema": schema,
        "profiles": profiles,
        "agents": agents,
        "decisions_r1": decisions_r1,
        "decisions_r2": decisions_r2,
        "decisions_r3": decisions_r3,
        "adversary_map": adversary_map,
        "valence": valence,
        "crisis_event": crisis_event,
        "resilience_metrics": resilience_metrics,
        "report_md": report_md,
        "timings": {
            "r1": dur_r1,
            "r2": dur_r2,
            "r3": dur_r3,
            "total": dur_r1 + dur_r2 + dur_r3,
        },
    }


async def run_swarm_simulation() -> None:
    client = OllamaClient(host=OLLAMA_HOST, model=DEFAULT_MODEL)
    if not await check_llm_provider(client):
        return

    console.print(
        Panel.fit(
            f"[bold magenta]Swarm Simulation Cockpit (Schema-First PoC)[/bold magenta]\n"
            f"Runs an Architect → Swarm → 3-Round debate → Crisis pipeline for any scenario.\n"
            f"Active model: [yellow]{DEFAULT_MODEL}[/yellow]\n",
            border_style="magenta",
            title="[bold]Simulation Cockpit[/bold]",
        )
    )

    console.print()
    console.print(
        "[bold yellow]Enter the concept, proposal, policy, pitch, or question you want simulated:[/bold yellow]"
    )
    console.print(
        "[dim]Examples: a product pitch, a draft policy, a hackathon idea, a strategic decision, "
        "a research question. The Architect will design the scenario vocabulary around your input.[/dim]"
    )
    stimulus = ask_multiline("Stimulus")
    if not stimulus.strip():
        console.print("[red]Stimulus cannot be empty. Returning to menu.[/red]")
        return

    agent_count = IntPrompt.ask(
        "[bold yellow]How many agent personas should populate the swarm? (1-20)[/bold yellow]",
        default=3,
    )
    if agent_count < 1:
        agent_count = 1

    concurrency = IntPrompt.ask(
        "[bold yellow]Max concurrent LLM threads (semaphore)[/bold yellow]",
        default=2,
    )

    console.print()
    try:
        await run_simulation_pipeline(client, stimulus, agent_count, concurrency)
    except SchemaDesignError as e:
        console.print(f"[red]Architect failed: {e}[/red]")
    except SwarmGenerationError as e:
        console.print(f"[red]Swarm generation failed: {e}[/red]")

    console.print("\n[dim]Press Enter to return to the main menu.[/dim]")
    try:
        input()
    except EOFError:
        pass
