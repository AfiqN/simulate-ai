import asyncio

import httpx
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule

from config import DEFAULT_MODEL, LLM_PROVIDER, OLLAMA_HOST, REQUEST_TIMEOUT
from src.cli import console
from src.cli.simulation import check_llm_provider, run_swarm_simulation
from src.llm.client import OllamaClient


async def run_chat_sandbox() -> None:
    client = OllamaClient(host=OLLAMA_HOST, model=DEFAULT_MODEL)
    if not await check_llm_provider(client):
        return

    host_display = "Google AI Studio" if LLM_PROVIDER == "gemini" else OLLAMA_HOST
    console.print(
        Panel.fit(
            f"[bold cyan]LLM Sandbox Chat[/bold cyan]\n"
            f"Provider: [green]{LLM_PROVIDER.upper()}[/green]\n"
            f"Model   : [yellow]{DEFAULT_MODEL}[/yellow]\n"
            f"Host    : [dim]{host_display}[/dim]\n\n"
            f"Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to return to the main menu.\n"
            f"Type [bold red]clear[/bold red] to reset conversation history.",
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
        except httpx.HTTPError as e:
            console.print(f"\n[red]Streaming error: {e}[/red]")
            messages.pop()
            continue
        messages.append({"role": "assistant", "content": full_response})


def main_menu() -> None:
    while True:
        console.clear()
        console.print(
            Panel.fit(
                "[bold cyan]SimulateAI — Multi-Agent Agentic Swarm Simulator[/bold cyan]\n"
                "Interactive CLI for the Behavioral Diagnostic Sandbox.\n\n"
                "1. [bold yellow]Start Sandbox Chat[/bold yellow] (1-on-1 LLM connection)\n"
                "2. [bold yellow]Start Swarm Simulation[/bold yellow] (schema-first 3-round simulation)\n"
                "3. [bold red]Exit[/bold red]",
                border_style="cyan",
                title="[bold]Main Cockpit Panel[/bold]",
            )
        )
        choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="2")
        if choice == "1":
            asyncio.run(run_chat_sandbox())
        elif choice == "2":
            asyncio.run(run_swarm_simulation())
        elif choice == "3":
            console.print("[dim]Exiting SimulateAI Cockpit. Goodbye.[/dim]")
            break
