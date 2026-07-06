import asyncio
import time
from collections import Counter
from typing import Any, Optional

from rich.live import Live
from rich.panel import Panel
from rich.prompt import IntPrompt
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table

from config import DEFAULT_MODEL, LLM_PROVIDER, MAX_CONCURRENCY, OLLAMA_HOST
from src.agent.adversary import compute_adversary_map, evolve_adversary_map
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
from src.report.compiler import ExecutiveCompiler, compute_resilience_metrics
from src.report.metrics import compute_quantitative_metrics
from src.report.sensitivity import compute_sensitivity_analysis
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
    depth: str = "standard",
) -> None:
    await asyncio.sleep(idx * 2)
    await _execute_round(
        idx,
        statuses,
        semaphore,
        in_progress_label="Thinking...",
        coroutine_factory=lambda: agent.perceive_and_react(stimulus, depth=depth),
    )


async def _run_debate(
    idx: int,
    agent: Agent,
    stimulus: str,
    round1_transcript: str,
    adversary: Optional[dict],
    statuses: list[dict],
    semaphore: asyncio.Semaphore,
    depth: str = "standard",
) -> None:
    await asyncio.sleep(4 + idx * 3)
    await _execute_round(
        idx,
        statuses,
        semaphore,
        in_progress_label="Debating...",
        coroutine_factory=lambda: agent.debate_and_react(
            stimulus, round1_transcript, adversary=adversary if adversary else None, depth=depth
        ),
    )


async def _run_crisis(
    idx: int,
    agent: Agent,
    crisis: str,
    original_stimulus: str,
    statuses: list[dict],
    semaphore: asyncio.Semaphore,
    depth: str = "standard",
) -> None:
    await asyncio.sleep(4 + idx * 3)
    await _execute_round(
        idx,
        statuses,
        semaphore,
        in_progress_label="Reacting...",
        coroutine_factory=lambda: agent.react_to_crisis(crisis, original_stimulus, depth=depth),
    )


async def _run_reconciliation(
    idx: int,
    agent: Agent,
    stimulus: str,
    full_transcript: str,
    statuses: list[dict],
    semaphore: asyncio.Semaphore,
    depth: str = "standard",
) -> None:
    await asyncio.sleep(2 + idx * 2)
    await _execute_round(
        idx,
        statuses,
        semaphore,
        in_progress_label="Reconciling...",
        coroutine_factory=lambda: agent.reconcile(stimulus, full_transcript, depth=depth),
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
        # Write result BEFORE status so _extract_decision never sees empty result for "Completed"
        statuses[idx]["result"] = result
        statuses[idx]["duration"] = time.time() - start
        statuses[idx]["status"] = "Failed" if "error" in result else "Completed"
    except Exception as e:
        statuses[idx]["result"] = {"error": str(e)}
        statuses[idx]["duration"] = time.time() - start
        statuses[idx]["status"] = "Failed"


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
            "utility_dimensions": {},
            "reasoning_chain": [],
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
        "utility_dimensions": result.get("utility_dimensions", {}),
        "reasoning_chain": result.get("reasoning_chain", []),
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


def _pick_valence(stimulus: str) -> str:
    """Legacy stub — no longer used. Dual events are always generated."""
    return "stress"


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


def _detect_language(text: str) -> str | None:
    """Detect if stimulus is written in a non-English language. Returns language name or None."""
    # Simple heuristic: check for common Indonesian/Malay markers
    indo_markers = {"dan", "yang", "untuk", "dengan", "dari", "ini", "itu", "akan",
                    "pada", "tidak", "atau", "juga", "sudah", "bisa", "ada", "ke",
                    "di", "agar", "serta", "oleh", "karena", "jika", "bahwa"}
    words = set(text.lower().split())
    indo_hits = words & indo_markers
    if len(indo_hits) >= 3 or (len(indo_hits) >= 2 and len(words) < 20):
        return "Indonesian"
    return None


def _apply_schema_overrides(schema, overrides: dict):
    """Apply user overrides to the generated schema, returning a new schema.

    Supported overrides:
        actions: list of {name, description, is_terminal} — replaces action list
        evaluation_dimensions: list of dimension names
        state_vocabulary: list of state names
    """
    from src.schema.simulation_schema import SimulationSchema, ActionDefinition

    data = schema.to_dict()

    if "actions" in overrides:
        data["actions"] = [
            {
                "name": str(a.get("name", "")).upper().strip(),
                "description": str(a.get("description", "")),
                "is_terminal": bool(a.get("is_terminal", False)),
                "affects_resource": a.get("affects_resource"),
            }
            for a in overrides["actions"]
            if a.get("name")
        ]

    if "evaluation_dimensions" in overrides:
        data["evaluation_dimensions"] = [str(d) for d in overrides["evaluation_dimensions"] if d]

    if "state_vocabulary" in overrides:
        data["state_vocabulary"] = [str(s) for s in overrides["state_vocabulary"] if s]

    return SimulationSchema.from_dict(data)


async def run_simulation_pipeline(
    client: OllamaClient,
    stimulus: str,
    agent_count: int,
    concurrency: int,
    crisis_override: Optional[str] = None,
    headless: bool = False,
    rag_enabled: Optional[bool] = None,
    progress_callback: Optional[Any] = None,
    event_callback: Optional[Any] = None,
    depth: str = "standard",
    schema_approval_callback: Optional[Any] = None,
) -> dict[str, Any]:
    concurrency = max(1, min(concurrency, MAX_CONCURRENCY))

    def _progress(msg: str):
        if progress_callback:
            progress_callback(msg)

    def _emit(event: dict):
        if event_callback:
            event_callback(event)

    # --- RAG Setup ---
    from src.rag.client import WebSearchClient
    from src.rag.query_gen import generate_perspective_queries, generate_crisis_query
    from src.rag.processor import process_search_results, extract_facts_with_llm
    from src.rag.models import RAGMetadata

    rag_client = None
    rag_metadata = RAGMetadata()
    if rag_enabled is not False:
        rag_client = WebSearchClient.create_if_available()

    # Detect stimulus language for report output
    stimulus_language = _detect_language(stimulus)

    if not headless:
        with Live(
            Spinner("aesthetic", text="[bold yellow]Architect is designing the simulation schema...[/bold yellow]"),
            refresh_per_second=10,
        ) as live:
            _progress("Designing simulation schema...")
            schema = await design_schema(client, stimulus)
            live.update("[bold green]✔ Schema designed.[/bold green]")
    else:
        _progress("Designing simulation schema...")
        _emit({"type": "stage", "stage": "schema", "progress": 0})
        schema = await design_schema(client, stimulus)

    # --- RAG: Post-Architect, Per-Role Perspectives ---
    swarm_rag_perspectives = None
    if rag_client:
        _progress("RAG: searching perspectives per role...")
        perspective_queries = await generate_perspective_queries(client, schema)
        all_perspectives: dict[str, list[str]] = {}
        all_query_strings: list[str] = []
        for cluster_id, queries in perspective_queries.items():
            cluster_facts: list[str] = []
            for qi, query in enumerate(queries):
                all_query_strings.append(query)
                # First query (index 0) is sentiment — allow social platforms
                is_sentiment = (qi == 0)
                results = await rag_client.search(query, allow_social=is_sentiment)
                if results:
                    processed = await extract_facts_with_llm(
                        client, results, query,
                        context=f"Scenario: {schema.scenario_name}. Role: {cluster_id}",
                        max_facts=4,
                    )
                    if processed.facts:
                        cluster_facts.extend(processed.facts)
            if cluster_facts:
                all_perspectives[cluster_id] = cluster_facts
        if all_perspectives:
            swarm_rag_perspectives = all_perspectives
            rag_metadata.record("post_architect_perspectives", all_query_strings, processed)

    if headless:
        _emit({"type": "schema_ready", "data": {"scenario_name": schema.scenario_name, "evaluation_dimensions": schema.evaluation_dimensions, "actions": [{"name": a.name, "is_terminal": a.is_terminal} for a in schema.actions]}})

    # --- Schema Approval Gate ---
    if schema_approval_callback:
        schema_overrides = await schema_approval_callback(schema)
        if schema_overrides:
            schema = _apply_schema_overrides(schema, schema_overrides)

    if not headless:
        render_schema_panel(schema)

        console.print()
        with Live(
            Spinner("aesthetic", text="[bold yellow]Generating agent personas...[/bold yellow]"),
            refresh_per_second=10,
        ) as live:
            _progress(f"Generating {agent_count} agent personas...")
            profiles = await generate_llm_swarm(client, schema, stimulus, agent_count, rag_perspectives=swarm_rag_perspectives)
            live.update("[bold green]✔ Personas generated.[/bold green]")
    else:
        _progress(f"Generating {agent_count} agent personas...")
        _emit({"type": "stage", "stage": "swarm", "progress": 16})
        profiles = await generate_llm_swarm(client, schema, stimulus, agent_count, rag_perspectives=swarm_rag_perspectives)

    agents = [Agent(profile, client, schema) for profile in profiles]
    if headless:
        _emit({"type": "swarm_ready", "agents": [{"id": p.agent_id, "archetype": p.archetype, "cluster_id": p.linguistic_cluster_id, "influence_weight": p.influence_weight, "backstory": p.backstory} for p in profiles]})
    if not headless:
        render_agent_table(profiles, schema)

    semaphore = asyncio.Semaphore(concurrency)

    # --- Round 1 ---
    _progress("Round 1: agents perceiving stimulus...")
    if headless:
        _emit({"type": "stage", "stage": "round1", "progress": 33})
    if not headless:
        console.print()
        console.print(Rule("[bold cyan]ROUND 1 — INITIAL PERCEPTION[/bold cyan]"))
    statuses_r1 = _make_statuses(agents)
    t0 = time.time()
    tasks_r1 = [
        asyncio.create_task(_run_perception(i, a, stimulus, statuses_r1, semaphore, depth=depth))
        for i, a in enumerate(agents)
    ]
    if not headless:
        await _drive_live_table(statuses_r1, "Round 1 Monitor", {"Thinking..."})
    await asyncio.gather(*tasks_r1)
    dur_r1 = time.time() - t0

    decisions_r1: list[dict] = []
    transcript_parts_r1: list[str] = []
    for i, a in enumerate(agents):
        d = _extract_decision(a, statuses_r1[i], schema)
        decisions_r1.append(d)
        if headless:
            _emit({"type": "agent_done", "round": 1, "data": d})
        if not headless:
            render_round_panel("Round 1 — Initial Perception", d, schema, statuses_r1[i]["duration"])
        transcript_parts_r1.append(
            f"Agent: {d['archetype']} (ID: {d['id']})\n"
            f"- Public Statement: \"{d['statement']}\"\n"
            f"- Action Committed: {d['action']}"
        )
    full_round1_transcript = "\n\n".join(transcript_parts_r1)

    if headless:
        _emit({"type": "round_summary", "round": 1, "data": {"decisions": decisions_r1, "vote_tally": dict(Counter(d["action"] for d in decisions_r1 if "error" not in d))}})

    adversary_map = compute_adversary_map(decisions_r1, agents)
    if not headless:
        console.print()
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

    # --- Round 2 (skipped in quick mode) ---
    dur_r2 = 0.0
    decisions_r2: list[dict] = []
    full_round2_transcript = full_round1_transcript  # fallback for quick mode

    if depth != "quick":
        _progress("Round 2: directed debate...")
        if headless:
            _emit({"type": "stage", "stage": "round2", "progress": 50})
        if not headless:
            console.print()
            console.print(Rule("[bold magenta]ROUND 2 — DIRECTED DEBATE[/bold magenta]"))
        statuses_r2 = _make_statuses(agents)
        t0 = time.time()
        tasks_r2 = [
            asyncio.create_task(_run_debate(
                i, a, stimulus, full_round1_transcript,
                adversary_map.get(a.profile.agent_id),
                statuses_r2, semaphore, depth=depth,
            ))
            for i, a in enumerate(agents)
        ]
        if not headless:
            await _drive_live_table(statuses_r2, "Round 2 Debate Monitor", {"Thinking...", "Debating..."})
        await asyncio.gather(*tasks_r2)
        dur_r2 = time.time() - t0

        for i, a in enumerate(agents):
            d = _extract_decision(a, statuses_r2[i], schema)
            decisions_r2.append(d)
            if headless:
                _emit({"type": "agent_done", "round": 2, "data": d})
            if not headless:
                render_round_panel("Round 2 — Directed Debate", d, schema, statuses_r2[i]["duration"])

        if headless:
            _emit({"type": "round_summary", "round": 2, "data": {"decisions": decisions_r2, "vote_tally": dict(Counter(d["action"] for d in decisions_r2 if "error" not in d))}})

        transcript_parts_r2 = [
            f"Agent: {d['archetype']} (ID: {d['id']})\n"
            f"- Public Statement: \"{d['statement']}\"\n"
            f"- Action: {d['action']}"
            for d in decisions_r2
        ]
        full_round2_transcript = "\n\n".join(transcript_parts_r2)

        # Evolve adversary map based on Round 2 shifts
        adversary_map = evolve_adversary_map(adversary_map, decisions_r1, decisions_r2, agents)
    else:
        # Quick mode: use R1 decisions as R2 stand-in for resilience comparison
        decisions_r2 = decisions_r1

    # --- RAG Point 3: Pre-Crisis ---
    crisis_rag_facts = None
    if rag_client and not crisis_override:
        queries = await generate_crisis_query(client, full_round2_transcript, schema)
        all_results = []
        for q in queries:
            all_results.extend(await rag_client.search(q))
        if all_results:
            processed = await extract_facts_with_llm(
                client, all_results, " | ".join(queries),
                context=f"Crisis scenario for: {schema.scenario_name}. Looking for real-world precedents and risk data.",
                max_facts=4,
            )
            crisis_rag_facts = processed.facts if processed.facts else None
            rag_metadata.record("pre_crisis", queries, processed)

    compiler = ExecutiveCompiler(client, schema)

    if crisis_override:
        # Backward compat: user-provided override is used as-is (single event)
        stress_event = crisis_override
        validation_event = None
    else:
        if not headless:
            await asyncio.sleep(2)
            with Live(
                Spinner("aesthetic", text="[bold red]Catalyst Agent synthesizing dual events...[/bold red]"),
                refresh_per_second=10,
            ) as live:
                stress_event, validation_event = await asyncio.gather(
                    compiler.generate_crisis_event(
                        stimulus, full_round2_transcript, valence="stress",
                        rag_crisis_facts=crisis_rag_facts,
                    ),
                    compiler.generate_crisis_event(
                        stimulus, full_round2_transcript, valence="validation",
                        rag_crisis_facts=crisis_rag_facts,
                    ),
                )
                live.update("[bold red]⚡ Dual Events Injected[/bold red]")
        else:
            stress_event, validation_event = await asyncio.gather(
                compiler.generate_crisis_event(
                    stimulus, full_round2_transcript, valence="stress",
                    rag_crisis_facts=crisis_rag_facts,
                ),
                compiler.generate_crisis_event(
                    stimulus, full_round2_transcript, valence="validation",
                    rag_crisis_facts=crisis_rag_facts,
                ),
            )

    # Build combined crisis string for agents
    if validation_event:
        crisis_event = f"NEGATIVE: {stress_event}\nPOSITIVE: {validation_event}"
    else:
        crisis_event = stress_event

    if not headless:
        console.print()
        console.print(
            Panel(
                f"[bold red]{stress_event}[/bold red]",
                title="[bold]⚡ External Stress Event[/bold]",
                border_style="red",
            )
        )
        if validation_event:
            console.print(
                Panel(
                    f"[bold green]{validation_event}[/bold green]",
                    title="[bold]⚡ External Validation Event[/bold]",
                    border_style="green",
                )
            )
    else:
        _emit({"type": "crisis", "stress_event": stress_event, "validation_event": validation_event})

    if headless:
        _emit({"type": "stage", "stage": "round3", "progress": 66})
    statuses_r3 = _make_statuses(agents)
    t0 = time.time()
    tasks_r3 = [
        asyncio.create_task(_run_crisis(i, a, crisis_event, stimulus, statuses_r3, semaphore, depth=depth))
        for i, a in enumerate(agents)
    ]
    if not headless:
        await _drive_live_table(statuses_r3, "Round 3 Crisis Monitor", {"Reacting..."})
    await asyncio.gather(*tasks_r3)
    dur_r3 = time.time() - t0

    decisions_r3: list[dict] = []
    for i, a in enumerate(agents):
        d = _extract_decision(a, statuses_r3[i], schema)
        decisions_r3.append(d)
        if headless:
            _emit({"type": "agent_done", "round": 3, "data": d})
        if not headless:
            render_round_panel("Round 3 — Crisis Reaction", d, schema, statuses_r3[i]["duration"])

    if headless:
        _emit({"type": "round_summary", "round": 3, "data": {"decisions": decisions_r3, "vote_tally": dict(Counter(d["action"] for d in decisions_r3 if "error" not in d))}})

    # --- Round 4: Reconciliation (deep mode only) ---
    decisions_r4: list[dict] = []
    dur_r4 = 0.0
    if depth == "deep":
        _progress("Round 4: reconciliation — seeking common ground...")
        if headless:
            _emit({"type": "stage", "stage": "round4", "progress": 75})
        if not headless:
            console.print()
            console.print(Rule("[bold green]ROUND 4 — RECONCILIATION[/bold green]"))

        # Build full transcript for reconciliation context
        all_transcript_parts = []
        for d in decisions_r1:
            all_transcript_parts.append(f"{d.get('archetype', '?')}: [{d.get('action')}] \"{d.get('statement', '')}\"")
        for d in decisions_r2:
            all_transcript_parts.append(f"{d.get('archetype', '?')}: [{d.get('action')}] \"{d.get('statement', '')}\"")
        for d in decisions_r3:
            all_transcript_parts.append(f"{d.get('archetype', '?')}: [{d.get('action')}] \"{d.get('statement', '')}\"")
        reconciliation_transcript = "\n".join(all_transcript_parts)

        statuses_r4 = _make_statuses(agents)
        t0 = time.time()
        tasks_r4 = [
            asyncio.create_task(_run_reconciliation(
                i, a, stimulus, reconciliation_transcript, statuses_r4, semaphore, depth=depth,
            ))
            for i, a in enumerate(agents)
        ]
        if not headless:
            await _drive_live_table(statuses_r4, "Round 4 Reconciliation Monitor", {"Reconciling..."})
        await asyncio.gather(*tasks_r4)
        dur_r4 = time.time() - t0

        for i, a in enumerate(agents):
            d = _extract_decision(a, statuses_r4[i], schema)
            decisions_r4.append(d)
            if headless:
                _emit({"type": "agent_done", "round": 4, "data": d})
            if not headless:
                render_round_panel("Round 4 — Reconciliation", d, schema, statuses_r4[i]["duration"])

        if headless:
            _emit({"type": "round_summary", "round": 4, "data": {"decisions": decisions_r4, "vote_tally": dict(Counter(d["action"] for d in decisions_r4 if "error" not in d))}})

    # --- Report compilation ---
    _progress("Compiling executive diagnostic report...")
    if headless:
        _emit({"type": "stage", "stage": "report", "progress": 83})
    resilience_metrics = compute_resilience_metrics(decisions_r2, decisions_r3, schema)
    if not headless:
        console.print()
        console.print(Rule("[bold yellow]COMPILING EXECUTIVE DIAGNOSTIC REPORT[/bold yellow]"))
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
                language=stimulus_language,
                depth=depth,
                profiles=profiles,
                round4_results=decisions_r4 or None,
            )
            live.update("[bold green]✔ Report compiled[/bold green]")
    else:
        report_md = await compiler.compile_report(
            stimulus, decisions_r1, decisions_r2,
            round3_results=decisions_r3, crisis_event=crisis_event,
            resilience_metrics=resilience_metrics,
            language=stimulus_language,
            depth=depth,
            profiles=profiles,
            round4_results=decisions_r4 or None,
        )

    if not headless:
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
        "decisions_r4": decisions_r4,
        "adversary_map": adversary_map,
        "crisis_event": {"stress": stress_event, "validation": validation_event},
        "resilience_metrics": resilience_metrics,
        "quantitative_metrics": compute_quantitative_metrics(
            decisions_r1, decisions_r2, decisions_r3, schema, profiles=profiles
        ),
        "sensitivity_analysis": compute_sensitivity_analysis(
            decisions_r1, decisions_r2, decisions_r3, profiles=profiles
        ),
        "report_md": report_md,
        "timings": {
            "r1": dur_r1,
            "r2": dur_r2,
            "r3": dur_r3,
            "r4": dur_r4,
            "total": dur_r1 + dur_r2 + dur_r3 + dur_r4,
        },
        "rag_metadata": rag_metadata.to_dict() if rag_metadata.injections else None,
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
    agent_count = max(1, min(agent_count, 20))

    concurrency = IntPrompt.ask(
        f"[bold yellow]Max concurrent LLM threads (1-{MAX_CONCURRENCY})[/bold yellow]",
        default=2,
    )
    concurrency = max(1, min(concurrency, MAX_CONCURRENCY))

    console.print()
    console.print(
        "[dim]Optional: inject a custom crisis event for Round 3 (leave blank for auto-generated):[/dim]"
    )
    crisis_input = ask_multiline("Crisis Override (optional)")
    crisis_override = crisis_input.strip() if crisis_input.strip() else None

    console.print()
    try:
        await run_simulation_pipeline(client, stimulus, agent_count, concurrency, crisis_override=crisis_override)
    except SchemaDesignError as e:
        console.print(f"[red]Architect failed: {e}[/red]")
    except SwarmGenerationError as e:
        console.print(f"[red]Swarm generation failed: {e}[/red]")

    console.print("\n[dim]Press Enter to return to the main menu.[/dim]")
    try:
        input()
    except EOFError:
        pass
