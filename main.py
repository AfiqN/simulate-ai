import asyncio
import sys
import time
from typing import List

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

from config import DEFAULT_MODEL, OLLAMA_HOST, REQUEST_TIMEOUT, LLM_PROVIDER
from src.llm.client import OllamaClient
from src.agent.profile import AgentProfile
from src.agent.agent import Agent
from src.agent.mock_agents import get_mock_agents, generate_custom_swarm, generate_llm_swarm
from src.agent.compiler import ExecutiveCompiler

console = Console()


async def check_ollama(client: OllamaClient) -> bool:
    """Check if the LLM backend is reachable."""
    host_display = "Google AI Studio" if LLM_PROVIDER == "gemini" else OLLAMA_HOST
    console.print(f"[dim]Connecting to {host_display}...[/dim]", end=" ")
    available = await client.is_available()
    if not available:
        console.print("[red]FAILED[/red]")
        if LLM_PROVIDER == "gemini":
            console.print(
                "[red]Error:[/red] Failed to authenticate with Gemini API Key.\n"
                "Please check your API key in config.py."
            )
        else:
            console.print(
                f"[red]Error:[/red] Ollama is not running at [yellow]{OLLAMA_HOST}[/yellow]\n"
                "Please make sure it's active. Start it with: [bold]ollama serve[/bold]"
            )
        return False
    console.print("[green]OK[/green]")
    return True


async def run_chat_sandbox():
    """Simple one-on-one chat sandbox wrapper."""
    client = OllamaClient(host=OLLAMA_HOST, model=DEFAULT_MODEL)
    if not await check_ollama(client):
        return

    host_display = "Google AI Studio" if LLM_PROVIDER == "gemini" else OLLAMA_HOST
    console.print(
        Panel.fit(
            f"[bold cyan]LLM Sandbox Chat[/bold cyan]\n"
            f"Provider: [green]{LLM_PROVIDER.upper()}[/green]\n"
            f"Model   : [yellow]{DEFAULT_MODEL}[/yellow]\n"
            f"Host    : [dim]{host_display}[/dim]\n\n"
            f"Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to return to main menu.\n"
            f"Type [bold red]clear[/bold red] to reset the conversation history.",
            border_style="cyan",
            title="[bold]Sandbox Chat[/bold]",
        )
    )

    messages: list[dict] = []

    while True:
        console.print()
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")
        except (EOFError, KeyboardInterrupt):
            break

        cmd = user_input.strip().lower()
        if cmd in ("exit", "quit", "q"):
            break

        if cmd == "clear":
            messages.clear()
            console.print(Rule("[dim]Conversation history cleared[/dim]"))
            continue

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})
        console.print(f"\n[bold magenta]AI[/bold magenta]  ", end="")

        full_response = ""
        try:
            async for chunk in client.chat_stream(messages, timeout=REQUEST_TIMEOUT):
                console.print(chunk, end="", markup=False)
                full_response += chunk
            console.print()
        except (httpx.HTTPError, Exception) as e:
            console.print(f"\n[red]Streaming error: {e}[/red]")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": full_response})


def render_agent_table(profiles: List[AgentProfile]):
    """Render a beautiful summary table of participating agents."""
    table = Table(title="Live Virtual Swarm Members", border_style="cyan")
    table.add_column("Agent ID", style="bold dim")
    table.add_column("Archetype", style="bold yellow")
    table.add_column("State", style="magenta")
    table.add_column("Key Attributes", style="cyan")
    table.add_column("Resource Pool", style="green")

    for p in profiles:
        attr = p.attributes
        res = p.resource_pool
        attr_str = f"Rat: {attr.rationality_index:.2f} | Agg: {attr.aggressiveness:.2f} | Risk: {attr.risk_tolerance:.2f}"
        res_str = f"{res.primary_resource_name}: {res.current_balance:,.0f}/{res.max_capacity:,.0f}"
        table.add_row(p.agent_id, p.archetype.replace("_", " "), p.current_internal_state, attr_str, res_str)

    console.print(table)


async def run_single_agent_task(idx: int, agent: Agent, stimulus: str, statuses: list, semaphore: asyncio.Semaphore):
    """Worker task to run agent perception and track its live status and duration with concurrency control."""
    # Rate-limiting: stagger Round 1 starts by agent index to spread API calls
    await asyncio.sleep(idx * 2)
    start_time = time.time()
    statuses[idx]["status"] = "Thinking..."
    try:
        async with semaphore:
            result = await agent.perceive_and_react(stimulus)
        duration = time.time() - start_time
        statuses[idx]["status"] = "Completed"
        statuses[idx]["duration"] = duration
        statuses[idx]["result"] = result
    except Exception as e:
        duration = time.time() - start_time
        statuses[idx]["status"] = "Failed"
        statuses[idx]["duration"] = duration
        statuses[idx]["result"] = {"error": str(e)}


async def run_single_agent_debate_task(
    idx: int, agent: Agent, stimulus: str, round1_transcript: str,
    adversary: dict, statuses: list, semaphore: asyncio.Semaphore
):
    """Worker task to run the directed debate round with adversary challenge injection and rate-limiting pacing."""
    # Rate-limiting: flat cool-off + index stagger to spread Round 2 API calls
    await asyncio.sleep(4 + idx * 3)
    start_time = time.time()
    statuses[idx]["status"] = "Debating..."
    try:
        async with semaphore:
            result = await agent.debate_and_react(
                stimulus, round1_transcript,
                adversary=adversary if adversary else None
            )
        duration = time.time() - start_time
        statuses[idx]["status"] = "Completed"
        statuses[idx]["duration"] = duration
        statuses[idx]["result"] = result
    except Exception as e:
        duration = time.time() - start_time
        statuses[idx]["status"] = "Failed"
        statuses[idx]["duration"] = duration
        statuses[idx]["result"] = {"error": str(e)}


async def run_single_agent_crisis_task(
    idx: int, agent: Agent, crisis: str, original_stimulus: str,
    statuses: list, semaphore: asyncio.Semaphore
):
    """Worker task to run the crisis stress-test round with rate-limiting pacing."""
    # Rate-limiting: flat cool-off + index stagger to spread Round 3 API calls
    await asyncio.sleep(4 + idx * 3)
    start_time = time.time()
    statuses[idx]["status"] = "Reacting..."
    try:
        async with semaphore:
            result = await agent.react_to_crisis(crisis, original_stimulus)
        duration = time.time() - start_time
        statuses[idx]["status"] = "Completed"
        statuses[idx]["duration"] = duration
        statuses[idx]["result"] = result
    except Exception as e:
        duration = time.time() - start_time
        statuses[idx]["status"] = "Failed"
        statuses[idx]["duration"] = duration
        statuses[idx]["result"] = {"error": str(e)}


def make_parallel_status_table(statuses: list, title: str = "Concurrent Execution Monitor") -> Table:
    """Render a dynamic live progress table of all concurrent agents."""
    table = Table(title=title, border_style="cyan")
    table.add_column("Agent ID", style="bold dim")
    table.add_column("Archetype", style="bold yellow")
    table.add_column("Processing Status", style="bold")
    table.add_column("Time Taken", style="green")

    for s in statuses:
        status_text = s["status"]
        if status_text == "Pending...":
            status_style = "[dim]Pending...[/dim]"
        elif status_text in ("Thinking...", "Debating...", "Reacting..."):
            status_style = f"[yellow]{status_text} ⏳[/yellow]"
        elif status_text == "Completed":
            status_style = "[green]✔ Completed[/green]"
        else:
            status_style = f"[red]❌ {status_text}[/red]"

        dur_text = f"{s['duration']:.2f}s" if s["duration"] > 0 else "---"
        table.add_row(s["id"], s["archetype"].replace("_", " "), status_style, dur_text)
    return table


def compute_adversary_map(decisions: list, agents: list) -> dict:
    """
    Compute the adversary map for each agent using:
    1. Cross-faction filtering (prefer opponents with different action decisions).
    2. Flat collapse fallback (if all took same action, skip filtering).
    3. Delta-U maximization (pick max |U_A - U_B|).
    4. Aggressiveness tie-breaker (if deltas are equal, pick most aggressive opponent).
    Returns: {agent_id: adversary_decision_dict or None}
    """
    adversary_map = {}
    for i, dec_a in enumerate(decisions):
        agent_a = agents[i]
        u_a = dec_a.get("utility", 0.0)
        action_a = dec_a.get("action", "IGNORE")

        # Step 1: gather candidates — prefer cross-faction (different action)
        cross_faction = [
            (j, dec_b) for j, dec_b in enumerate(decisions)
            if j != i and dec_b.get("action", "IGNORE") != action_a
        ]
        candidates = cross_faction if cross_faction else [
            (j, dec_b) for j, dec_b in enumerate(decisions) if j != i
        ]

        if not candidates:
            adversary_map[dec_a["id"]] = None
            continue

        # Step 2: find max delta U
        max_delta = max(abs(u_a - dec_b.get("utility", 0.0)) for _, dec_b in candidates)

        # Step 3: tie-breaker — collect all candidates with max delta, pick highest aggressiveness
        tied = [
            (j, dec_b) for j, dec_b in candidates
            if abs(u_a - dec_b.get("utility", 0.0)) == max_delta
        ]
        if len(tied) > 1:
            _, chosen = max(tied, key=lambda x: agents[x[0]].profile.attributes.aggressiveness)
        else:
            _, chosen = tied[0]

        adversary_map[dec_a["id"]] = chosen

    return adversary_map


async def run_swarm_simulation_poc():
    """Simulate multiple agents evaluating a single user stimulus concept in dynamic multi-round debates."""
    from rich.prompt import IntPrompt

    client = OllamaClient(host=OLLAMA_HOST, model=DEFAULT_MODEL)
    if not await check_ollama(client):
        return

    console.print(
        Panel.fit(
            f"[bold magenta]Swarm Simulation Cockpit (PoC - Live Swarm Engine)[/bold magenta]\n"
            f"This mode runs multi-round dynamic debates & synthesizes automated diagnostic reports.\n"
            f"Using local model: [yellow]{DEFAULT_MODEL}[/yellow]\n",
            border_style="magenta",
            title="[bold]Simulation Cockpit[/bold]",
        )
    )

    # Ask user for simulation stimulus
    console.print()
    console.print("[bold yellow]Enter a prompt / concept / product pitch / policy to put to test:[/bold yellow]")
    console.print("[dim]Example: 'Healthy catering daily subscription for IDR 100,000/week with free shipping.'[/dim]")
    stimulus = Prompt.ask("[bold green]Concept Stimulus[/bold green]")

    if not stimulus.strip():
        console.print("[red]Concept cannot be empty. Returning to menu.[/red]")
        return

    # Choose size of the swarm to simulate parallel scaling
    count = IntPrompt.ask(
        "[bold yellow]How many dynamic agent personas do you want to generate? (e.g. 1-20)[/bold yellow]",
        default=3,
    )
    if count < 1:
        count = 1

    # Initialize dynamic swarm using LLM agent generation
    console.print()
    with Live(Spinner("aesthetic", text="[bold yellow]Generating custom agent personas tailored to your concept...[/bold yellow]"), refresh_per_second=10) as live:
        profiles = await generate_llm_swarm(client, stimulus, count)
        live.update("[bold green]✔ Dynamic agent personas generated successfully![/bold green]")

    agents = [Agent(profile, client) for profile in profiles]

    render_agent_table(profiles)

    # Limit the number of concurrent active LLM inquiries to prevent Ollama context/response timeout
    # A limit of 2 or 3 is highly recommended for consumer GPUs (RTX 3060) to keep model response time fast.
    concurrency_limit = IntPrompt.ask(
        "[bold yellow]Set maximum concurrent LLM threads (Semaphore Limit)[/bold yellow]",
        default=2,
    )
    semaphore = asyncio.Semaphore(concurrency_limit)

    # ==========================================
    # ROUND 1: INITIAL PERCEPTION (PARALLEL)
    # ==========================================
    console.print()
    console.print(Rule("[bold cyan]ROUND 1: INITIAL PERCEPTIONS STARTED[/bold cyan]"))

    statuses_r1 = [{
        "id": agent.profile.agent_id,
        "archetype": agent.profile.archetype,
        "status": "Pending...",
        "duration": 0.0,
        "result": {}
    } for agent in agents]

    global_start_time_r1 = time.time()

    # Launch concurrent asyncio tasks as background Tasks
    tasks_r1 = [
        asyncio.create_task(run_single_agent_task(idx, agent, stimulus, statuses_r1, semaphore))
        for idx, agent in enumerate(agents)
    ]

    # Live feed of status maps for Round 1
    with Live(make_parallel_status_table(statuses_r1, "Round 1 Monitor"), refresh_per_second=5) as live:
        # Keep updating live table while we wait for all tasks to finish concurrently
        while any(s["status"] in ("Pending...", "Thinking...") for s in statuses_r1):
            await asyncio.sleep(0.2)
            live.update(make_parallel_status_table(statuses_r1, "Round 1 Monitor"))
        
        # Ensure all tasks are completed and gather any final results
        await asyncio.gather(*tasks_r1)
        live.update(make_parallel_status_table(statuses_r1, "Round 1 Monitor"))

    global_duration_r1 = time.time() - global_start_time_r1

    # Format decisions and public transcript from Round 1
    decisions_r1 = []
    round1_transcript_parts = []

    for idx, agent in enumerate(agents):
        archetype_title = agent.profile.archetype.replace("_", " ")
        result = statuses_r1[idx]["result"]

        if "error" in result or not result:
            decisions_r1.append({
                "id": agent.profile.agent_id,
                "archetype": archetype_title,
                "action": "IGNORE",
                "utility": 0.0,
                "monologue": f"Error: {result.get('error', 'No response received' if not result else 'Unknown error')}",
                "statement": "I have reservations and need more time to think about this.",
                "new_state": agent.profile.current_internal_state
            })
            round1_transcript_parts.append(
                f"Agent: {archetype_title} (ID: {agent.profile.agent_id})\n"
                f"- Public Statement: \"I have reservations and need more time to think about this.\"\n"
                f"- Action Committed: IGNORE"
            )
            continue

        monologue = result.get("internal_monologue", "...")
        statement = result.get("public_reaction", "...")
        action = result.get("action_decision", "IGNORE")
        new_state = result.get("new_internal_state", "Neutral")

        weights = result.get("utility_weights", {})
        vals = result.get("stimulus_evaluated_values", {})

        w_savings = weights.get("w_savings", 0.0)
        w_urgency = weights.get("w_urgency", 0.0)
        w_ego = weights.get("w_ego", 0.0)

        v_gains = vals.get("v_gains", 0.0)
        v_urgency = vals.get("v_urgency", 0.0)
        v_ego = vals.get("v_ego", 0.0)
        cost = vals.get("cost", 0.0)

        utility = (w_savings * v_gains) + (w_urgency * v_urgency) + (w_ego * v_ego) - cost

        decisions_r1.append({
            "id": agent.profile.agent_id,
            "archetype": archetype_title,
            "action": action,
            "utility": utility,
            "monologue": monologue,
            "statement": statement,
            "new_state": new_state
        })

        # Append structured transcript for peers to read in Round 2
        round1_transcript_parts.append(
            f"Agent: {archetype_title} (ID: {agent.profile.agent_id})\n"
            f"- Public Statement: \"{statement}\"\n"
            f"- Action Committed: {action}"
        )

    full_round1_transcript = "\n\n".join(round1_transcript_parts)

    # Show a brief feed compilation of Round 1
    console.print()
    console.print(Panel(
        f"[dim]The community has evaluated your concept. Differing perspectives are highly visible.[/dim]\n"
        f"A total of [yellow]{len(decisions_r1)}[/yellow] agents successfully entered the conversational space.\n"
        f"Deploying social transcripts to all agents to begin Round 2...",
        title="[bold cyan]Round 1 Summary: Chaos Feed[/bold cyan]",
        border_style="cyan"
    ))

    # ==========================================
    # COMPUTE ADVERSARY MAP (DIRECTED DEBATE GRAPH)
    # ==========================================
    console.print()
    adversary_map = compute_adversary_map(decisions_r1, agents)
    console.print(Panel(
        "\n".join([
            f"[bold yellow]{decisions_r1[i]['archetype']}[/bold yellow] → challenges → "
            f"[bold red]{adversary_map[decisions_r1[i]['id']]['archetype'] if adversary_map[decisions_r1[i]['id']] else 'No adversary (homogeneous swarm)'}[/bold red]"
            for i in range(len(agents))
        ]),
        title="[bold cyan]Directed Interaction Graph (ΔU Pairing)[/bold cyan]",
        border_style="cyan"
    ))

    # ==========================================
    # ROUND 2: DIRECTED SWARM DEBATE (PARALLEL)
    # ==========================================
    console.print()
    console.print(Rule("[bold magenta]ROUND 2: DIRECTED DEBATE & REFLECTION STARTED[/bold magenta]"))

    statuses_r2 = [{
        "id": agent.profile.agent_id,
        "archetype": agent.profile.archetype,
        "status": "Pending...",
        "duration": 0.0,
        "result": {}
    } for agent in agents]

    global_start_time_r2 = time.time()

    # Launch tasks for Round 2 with adversary assignments
    tasks_r2 = [
        asyncio.create_task(run_single_agent_debate_task(
            idx, agent, stimulus, full_round1_transcript,
            adversary_map.get(agent.profile.agent_id),
            statuses_r2, semaphore
        ))
        for idx, agent in enumerate(agents)
    ]

    # Live feed of status maps for Round 2
    with Live(make_parallel_status_table(statuses_r2, "Round 2 Debate Monitor"), refresh_per_second=5) as live:
        while any(s["status"] in ("Pending...", "Thinking...", "Debating...") for s in statuses_r2):
            await asyncio.sleep(0.2)
            live.update(make_parallel_status_table(statuses_r2, "Round 2 Debate Monitor"))
        
        await asyncio.gather(*tasks_r2)
        live.update(make_parallel_status_table(statuses_r2, "Round 2 Debate Monitor"))

    global_duration_r2 = time.time() - global_start_time_r2

    # Process Round 2 Decisions
    decisions_r2 = []
    for idx, agent in enumerate(agents):
        archetype_title = agent.profile.archetype.replace("_", " ")
        result = statuses_r2[idx]["result"]

        if "error" in result or not result:
            decisions_r2.append({
                "id": agent.profile.agent_id,
                "archetype": archetype_title,
                "action": "IGNORE",
                "utility": 0.0,
                "monologue": "Failed to engage in debate.",
                "statement": "...",
                "new_state": agent.profile.current_internal_state,
                "balance": agent.profile.resource_pool.current_balance,
                "duration": statuses_r2[idx]["duration"]
            })
            continue

        monologue = result.get("internal_monologue", "...")
        statement = result.get("public_reaction", "...")
        action = result.get("action_decision", "IGNORE")
        new_state = result.get("new_internal_state", "Neutral")
        new_memory = result.get("new_memory_to_store", "No memory stored.")

        weights = result.get("utility_weights", {})
        vals = result.get("stimulus_evaluated_values", {})

        w_savings = weights.get("w_savings", 0.0)
        w_urgency = weights.get("w_urgency", 0.0)
        w_ego = weights.get("w_ego", 0.0)

        v_gains = vals.get("v_gains", 0.0)
        v_urgency = vals.get("v_urgency", 0.0)
        v_ego = vals.get("v_ego", 0.0)
        cost = vals.get("cost", 0.0)

        utility = (w_savings * v_gains) + (w_urgency * v_urgency) + (w_ego * v_ego) - cost
        action_style = "green" if action in ("BUY", "COLLABORATE") else "red" if action == "REJECT" else "yellow"

        decisions_r2.append({
            "id": agent.profile.agent_id,
            "archetype": archetype_title,
            "action": action,
            "utility": utility,
            "monologue": monologue,
            "statement": statement,
            "new_state": new_state,
            "balance": agent.profile.resource_pool.current_balance,
            "duration": statuses_r2[idx]["duration"]
        })

        # Render debate output panel to user
        console.print(
            Panel(
                f"[italic dim]Secret Debate Reflection (Internal Logic):[/italic dim]\n"
                f"[dim]\"{monologue}\"[/dim]\n\n"
                f"[bold cyan]Public Statement (Response to peers):[/bold cyan]\n"
                f"\"{statement}\"\n\n"
                f"--- [bold]Utility Parameters (Formula Evaluation)[/bold] ---\n"
                f"• Utility (U) : [bold]{utility:.4f}[/bold]\n"
                f"• Decision    : [{action_style}][bold]{action}[/bold][/{action_style}]\n"
                f"• State Transition: [magenta]{new_state}[/magenta]\n"
                f"• Saved Memory: [cyan italic]{new_memory}[/cyan italic]\n"
                f"• Agent Speed : [green]{statuses_r2[idx]['duration']:.2f} seconds[/green]",
                title=f"[bold yellow]{archetype_title} (ID: {agent.profile.agent_id}) - Round 2 (Debate)[/bold yellow]",
                border_style="cyan" if action in ("BUY", "COLLABORATE") else "red" if action == "REJECT" else "yellow"
            )
        )

    # ==========================================
    # ROUND 3: CRISIS SYNTHESIS & STRESS-TEST
    # ==========================================
    console.print()
    console.print(Rule("[bold red]ROUND 3: CRISIS STRESS-TEST INITIATED[/bold red]"))

    # Build Round 2 transcript for crisis synthesis input
    round2_transcript_parts = [
        f"Agent: {d['archetype']} (ID: {d['id']})\n"
        f"- Public Statement: \"{d['statement']}\"\n"
        f"- Action: {d['action']}"
        for d in decisions_r2
    ]
    full_round2_transcript = "\n\n".join(round2_transcript_parts)

    # Rate-limit: brief pause before crisis synthesis API call
    await asyncio.sleep(2)

    compiler = ExecutiveCompiler(client)
    with Live(Spinner("aesthetic", text="[bold red]Catalyst Agent synthesizing crisis event...[/bold red]"), refresh_per_second=10) as live:
        crisis_event = await compiler.generate_crisis_event(stimulus, full_round2_transcript)
        live.update(f"[bold red]⚡ Crisis Event Injected![/bold red]")

    console.print()
    console.print(Panel(
        f"[bold red]{crisis_event}[/bold red]",
        title="[bold]⚡ External Catalyst Event — Injected by System[/bold]",
        border_style="red"
    ))

    statuses_r3 = [{
        "id": agent.profile.agent_id,
        "archetype": agent.profile.archetype,
        "status": "Pending...",
        "duration": 0.0,
        "result": {}
    } for agent in agents]

    global_start_time_r3 = time.time()

    tasks_r3 = [
        asyncio.create_task(run_single_agent_crisis_task(
            idx, agent, crisis_event, stimulus, statuses_r3, semaphore
        ))
        for idx, agent in enumerate(agents)
    ]

    with Live(make_parallel_status_table(statuses_r3, "Round 3 Crisis Monitor"), refresh_per_second=5) as live:
        while any(s["status"] in ("Pending...", "Reacting...") for s in statuses_r3):
            await asyncio.sleep(0.2)
            live.update(make_parallel_status_table(statuses_r3, "Round 3 Crisis Monitor"))
        await asyncio.gather(*tasks_r3)
        live.update(make_parallel_status_table(statuses_r3, "Round 3 Crisis Monitor"))

    global_duration_r3 = time.time() - global_start_time_r3

    decisions_r3 = []
    for idx, agent in enumerate(agents):
        archetype_title = agent.profile.archetype.replace("_", " ")
        result = statuses_r3[idx]["result"]

        if "error" in result or not result:
            decisions_r3.append({
                "id": agent.profile.agent_id,
                "archetype": archetype_title,
                "action": "IGNORE",
                "utility": 0.0,
                "monologue": "Failed to react to crisis.",
                "statement": "...",
                "new_state": str(agent.profile.current_internal_state),
                "duration": statuses_r3[idx]["duration"]
            })
            continue

        monologue = result.get("internal_monologue", "...")
        statement = result.get("public_reaction", "...")
        action = result.get("action_decision", "IGNORE")
        new_state = result.get("new_internal_state", "Neutral")
        new_memory = result.get("new_memory_to_store", "No memory stored.")
        weights = result.get("utility_weights", {})
        vals = result.get("stimulus_evaluated_values", {})
        utility = (
            weights.get("w_savings", 0.0) * vals.get("v_gains", 0.0)
            + weights.get("w_urgency", 0.0) * vals.get("v_urgency", 0.0)
            + weights.get("w_ego", 0.0) * vals.get("v_ego", 0.0)
            - vals.get("cost", 0.0)
        )
        action_style = "green" if action in ("BUY", "COLLABORATE") else "red" if action == "REJECT" else "yellow"

        decisions_r3.append({
            "id": agent.profile.agent_id,
            "archetype": archetype_title,
            "action": action,
            "utility": utility,
            "monologue": monologue,
            "statement": statement,
            "new_state": new_state,
            "duration": statuses_r3[idx]["duration"]
        })

        console.print(
            Panel(
                f"[italic dim]Crisis Internal Monologue:[/italic dim]\n"
                f"[dim]\"{monologue}\"[/dim]\n\n"
                f"[bold red]Crisis Public Reaction:[/bold red]\n"
                f"\"{statement}\"\n\n"
                f"• Utility (U) : [bold]{utility:.4f}[/bold]\n"
                f"• Decision    : [{action_style}][bold]{action}[/bold][/{action_style}]\n"
                f"• State       : [magenta]{new_state}[/magenta]\n"
                f"• Memory      : [cyan italic]{new_memory}[/cyan italic]",
                title=f"[bold red]{archetype_title} (ID: {agent.profile.agent_id}) - Round 3 (Crisis Reaction)[/bold red]",
                border_style="red" if action == "REJECT" else "yellow" if action == "IGNORE" else "green"
            )
        )

    # ==========================================
    # EXECUTIVE DIAGNOSTIC REPORT COMPILATION
    # ==========================================
    console.print()
    console.print(Rule("[bold yellow]COMPILING EXECUTIVE DIAGNOSTIC REPORT[/bold yellow]"))

    await asyncio.sleep(2)

    with Live(Spinner("aesthetic", text="[bold yellow]Chief Behavioral Architect is analyzing all three rounds...[/bold yellow]"), refresh_per_second=10) as live:
        report_md = await compiler.compile_report(
            stimulus, decisions_r1, decisions_r2,
            round3_results=decisions_r3, crisis_event=crisis_event
        )
        live.update("[bold green]✔ Diagnostic Report compiled successfully![/bold green]")

    console.print()
    console.print(
        Panel(
            report_md,
            title="[bold yellow]SIMULATEAI EXECUTIVE DIAGNOSTIC REPORT[/bold yellow]",
            border_style="yellow",
            expand=True
        )
    )

    console.print(Rule("[bold magenta]SIMULATION CONCLUDED[/bold magenta]"))
    console.print(
        f"• Round 1 Time   : [green]{global_duration_r1:.2f}s[/green]\n"
        f"• Round 2 Time   : [green]{global_duration_r2:.2f}s[/green]\n"
        f"• Round 3 Time   : [green]{global_duration_r3:.2f}s[/green]\n"
        f"• Total Duration : [yellow]{global_duration_r1 + global_duration_r2 + global_duration_r3:.2f}s[/yellow] "
        f"for [yellow]{count}[/yellow] agents across 3 rounds.\n"
    )

    # 3-round comparison summary table
    r1_lookup = {d["id"]: d for d in decisions_r1}
    r2_lookup = {d["id"]: d for d in decisions_r2}
    r3_lookup = {d["id"]: d for d in decisions_r3}

    res_table = Table(title="3-Round Simulation Verdict Comparison", border_style="magenta")
    res_table.add_column("Agent Archetype", style="bold yellow")
    res_table.add_column("R1 Initial", style="bold")
    res_table.add_column("R2 Debate", style="bold")
    res_table.add_column("R3 Crisis", style="bold")
    res_table.add_column("Final State", style="magenta")
    res_table.add_column("Resources", style="green")

    def action_tag(action: str) -> str:
        color = "green" if action in ("BUY", "COLLABORATE") else "red" if action == "REJECT" else "yellow"
        return f"[{color}]{action}[/{color}]"

    for d in decisions_r3:
        aid = d["id"]
        r1 = r1_lookup.get(aid, {})
        r2 = r2_lookup.get(aid, {})
        balance = agents[next(i for i, a in enumerate(agents) if a.profile.agent_id == aid)].profile.resource_pool.current_balance
        res_table.add_row(
            d["archetype"],
            action_tag(r1.get("action", "?")),
            action_tag(r2.get("action", "?")),
            action_tag(d["action"]),
            d["new_state"],
            f"{balance:,.0f}"
        )

    console.print(res_table)
    console.print("\n[dim]Press Enter to return to main menu.[/dim]")
    input()


def main_menu():
    """Main terminal loop entry point."""
    while True:
        console.clear()
        console.print(
            Panel.fit(
                "[bold cyan]SimulateAI — Multi-Agent Agentic Swarm Simulator[/bold cyan]\n"
                "Interactive CLI Interface of the Behavioral Diagnostic Sandbox\n\n"
                "1. [bold yellow]Start Interactive Sandbox Chat[/bold yellow] (1-on-1 LLM connection)\n"
                "2. [bold yellow]Start Mini-Swarm Behavior Simulation[/bold yellow] (Local PoC Swarm)\n"
                "3. [bold red]Exit / Quit[/bold red]",
                border_style="cyan",
                title="[bold]Main Cockpit Panel[/bold]",
            )
        )

        choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="2")

        if choice == "1":
            asyncio.run(run_chat_sandbox())
        elif choice == "2":
            asyncio.run(run_swarm_simulation_poc())
        elif choice == "3":
            console.print("[dim]Exiting SimulateAI Cockpit. Goodbye![/dim]")
            break


if __name__ == "__main__":
    main_menu()
