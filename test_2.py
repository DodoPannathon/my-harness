import asyncio
import json
import os

import aiohttp
from dotenv import load_dotenv
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

load_dotenv()

URL = os.getenv("URLS")
API_KEY = os.getenv("API_KEY")
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

console = Console()


def format_conversation(conversation: list) -> Text:
    """Format conversation history with Rich styling."""
    parts = []
    for msg in conversation:
        role = msg["role"]
        content = msg["content"]
        if role == "assistant":
            parts.append(Text(f"{content}", style="dim"))
        else:
            parts.append(Text(f"{content}", style="blue"))
    return Text("\n").join(parts)


def render_footer(current_input: str = "") -> Text:
    """Render the command bar footer in dim style."""
    sep = "-" * 53
    return Text(f"\n{sep}\n> {current_input}\n{sep}\n/list /continue /save /exit\n", style="dim")


def build_live_content(conversation: list, current_input: str = "") -> Group:
    """Build the renderable for Live with conversation + footer."""
    return Group(
        Panel(format_conversation(conversation), border_style="dim"),
        render_footer(current_input),
    )


async def fatch_data():
    conversation = []

    live = Live(
        build_live_content(conversation),
        console=console,
        refresh_per_second=10,
        screen=False,
    )
    live.start()

    while True:
        live.stop()
        print()
        prompt = input("> ")
        print()
        live.update(build_live_content(conversation, prompt))
        live.start()

        conversation.append({"role": "user", "content": prompt})

        payload = {
            "model": "qwen3.6-35b-a3b",
            "messages": conversation,
            "stream": True,
        }

        full_response = ""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{URL}/v1/chat/completions", json=payload, headers=headers
            ) as response:
                async for line in response.content:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("choices"):
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                                    print(content, end="", flush=True)
                                    live.update(build_live_content(conversation))
                        except (json.JSONDecodeError, KeyError):
                            pass

        print()
        conversation.append({"role": "assistant", "content": full_response})
        live.update(build_live_content(conversation))
        live.start()


if __name__ == "__main__":
    asyncio.run(fatch_data())
