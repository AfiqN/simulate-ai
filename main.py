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
    start_time = time.time()
    statuses[idx]["status"] = "Thinking..."
    try:
        # Acquire semaphore before calling the heavy LLM API
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


async def run_single_agent_debate_task(idx: int, agent: Agent, stimulus: str, round1_transcript: str, statuses: list, semaphore: asyncio.Semaphore):
    """Worker task to run agent debate round and track its live status and duration with concurrency control."""
    start_time = time.time()
    statuses[idx]["status"] = "Debating..."
    try:
        # Acquire semaphore before calling the heavy LLM API
        async with semaphore:
            result = await agent.debate_and_react(stimulus, round1_transcript)
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
        elif status_text == "Thinking..." or status_text == "Debating...":
            status_style = f"[yellow]{status_text} ⏳[/yellow]"
        elif status_text == "Completed":
            status_style = "[green]✔ Completed[/green]"
        else:
            status_style = f"[red]❌ {status_text}[/red]"

        dur_text = f"{s['duration']:.2f}s" if s["duration"] > 0 else "---"
        table.add_row(s["id"], s["archetype"].replace("_", " "), status_style, dur_text)
    return table


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
    # ROUND 2: DYNAMIC SWARM DEBATE (PARALLEL)
    # ==========================================
    console.print()
    console.print(Rule("[bold magenta]ROUND 2: DYNAMIC DEBATE & REFLECTION STARTED[/bold magenta]"))

    statuses_r2 = [{
        "id": agent.profile.agent_id,
        "archetype": agent.profile.archetype,
        "status": "Pending...",
        "duration": 0.0,
        "result": {}
    } for agent in agents]

    global_start_time_r2 = time.time()

    # Launch tasks for Round 2
    tasks_r2 = [
        asyncio.create_task(run_single_agent_debate_task(idx, agent, stimulus, full_round1_transcript, statuses_r2, semaphore))
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
    # ROUND 3: EXECUTIVE DIAGNOSTIC REPORT CONTROLLER
    # ==========================================
    console.print()
    console.print(Rule("[bold yellow]COMPILING EXECUTIVE DIAGNOSTIC REPORT[/bold yellow]"))

    with Live(Spinner("aesthetic", text="[bold yellow]Chief Behavioral Architect is analyzing transcripts...[/bold yellow]"), refresh_per_second=10) as live:
        compiler = ExecutiveCompiler(client)
        report_md = await compiler.compile_report(stimulus, decisions_r1, decisions_r2)
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
    console.print(f"• Round 1 Time   : [green]{global_duration_r1:.2f}s[/green]\n"
                  f"• Round 2 Time   : [green]{global_duration_r2:.2f}s[/green]\n"
                  f"• Total Duration : [yellow]{global_duration_r1 + global_duration_r2:.2f}s[/yellow] for [yellow]{count}[/yellow] agents.\n")

    # Consolidate results into summary table
    res_table = Table(title="Simulation Verdict Summary (Parallel Engine — End of Debate)", border_style="magenta")
    res_table.add_column("Agent Archetype", style="bold yellow")
    res_table.add_column("Decision Taken", style="bold")
    res_table.add_column("Calculated Utility", style="bold cyan")
    res_table.add_column("Ending Emotional State", style="magenta")
    res_table.add_column("Remaining Resources", style="green")

    for dec in decisions_r2:
        act_style = "green" if dec["action"] in ("BUY", "COLLABORATE") else "red" if dec["action"] == "REJECT" else "yellow"
        res_table.add_row(
            dec["archetype"],
            f"[{act_style}]{dec['action']}[/{act_style}]",
            f"{dec['utility']:.4f}",
            dec["new_state"],
            f"{dec['balance']:,.0f}"
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
