"""
Ollama Cloud AI Client - OpenAI Compatible Mode
Interactive model selector with async HTTP requests and spinner
Uses OpenAI /v1/chat/completions API format
"""

import ast
import asyncio
import json
import os
from pathlib import Path

import aiohttp
import inquirer
from dotenv import load_dotenv

load_dotenv()

# Configuration
URL = os.getenv("URLS", "")
API_KEY = os.getenv("API_KEY", "")
BASE_PATH = Path(__file__).resolve().parent
CONVERSATION_PATH = BASE_PATH / "conversations"

if not CONVERSATION_PATH.exists():
    CONVERSATION_PATH.mkdir()

headers = {
    "Authorization": "Bearer " + API_KEY,
    "Content-Type": "application/json",
}


async def select_model(url: str) -> str | None:
    """
    Fetch available models from Ollama API and let user select one.

    Args:
        url: Base URL of the Ollama API

    Returns:
        Selected model name or None if selection failed
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/v1/models", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    models = [m["id"] for m in result.get("data", [])]

                    if not models:
                        print("No models available on server")
                        return None

                    question = [
                        inquirer.List(
                            "model",
                            message="Select a model",
                            choices=models,
                        )
                    ]

                    answer = inquirer.prompt(question)

                    if answer:
                        selected_model = answer["model"]
                        print(f"\n✓ You selected: {selected_model}")
                        return selected_model
                    else:
                        print("\nNo selection made")
                        return None
                else:
                    print(f"Failed to fetch model data: {response.status}")
                    return None

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return None
    except aiohttp.ClientError as e:
        print(f"Network error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


async def spinner_task():
    """Display a loading spinner animation."""
    SPINNER_CHARS = "|/-\\"
    try:
        while True:
            for char in SPINNER_CHARS:
                print(f"\r{char}", end="", flush=True)
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass


def convert_title_file(title: str) -> str:
    return f"{title.replace(' ', '_')}.txt"


def get_sorted_sessions() -> list[str]:
    """Get session files sorted by modification time, newest first."""
    sessions = []
    for item in CONVERSATION_PATH.iterdir():
        if item.is_file() and item.suffix == ".txt":
            mtime = item.stat().st_mtime
            name = item.stem
            sessions.append((name, mtime))
    sessions.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in sessions]


def format_sessions(sessions: list[str]) -> str:
    """Format sessions as numbered list."""
    if not sessions:
        return "No previous conversation"
    max_num = len(sessions)
    width = len(str(max_num))
    lines = []
    for i, name in enumerate(sessions, 1):
        lines.append(f" {str(i).rjust(width)}. {name}")
    return "\n".join(lines)


def render_footer(text: str) -> None:
    """Render text on the footer line (second-to-last line, above input prompt)."""
    print(" " * 80, end="\r", flush=True)
    print(f"\033[90m{text}\033[0m", end="", flush=True)
    print("\033[F", end="")


def continue_command(title: str) -> list:
    with open(CONVERSATION_PATH / title, "r", encoding="utf-8") as file:
        print("=" * 50)
        context = []
        lines = file.readlines()
        for line in lines:
            line_object = ast.literal_eval(line.rstrip("\n"))
            context.append(line_object)
            if line_object["role"] == "user":
                print(f"> {line_object['content']}")
            elif line_object["role"] == "assistant":
                print(line_object["content"])
            print("=" * 50)
        return context


COMMANDS_FOOTER = "/list      /continue      /save      /exit"


async def prompt_input(context: list, session_name: str) -> tuple[list, str, str]:
    """Prompt user for input asynchronously and handle commands."""

    prompt = await asyncio.get_event_loop().run_in_executor(None, lambda: input("> "))

    if prompt == "/list":
        sessions = get_sorted_sessions()
        render_footer(format_sessions(sessions))
        return context, "", session_name
    elif prompt[:9] == "/continue":
        conv_name = prompt[9:].strip()
        if conv_name:
            session_name = convert_title_file(conv_name)
            context = continue_command(session_name)
            render_footer(COMMANDS_FOOTER)
            return context, "", session_name

        sessions = get_sorted_sessions()
        if not sessions:
            render_footer("No previous conversation")
            return context, "", session_name

        render_footer(format_sessions(sessions))

        question = [
            inquirer.List(
                "conversation",
                message="Select a previous conversation",
                choices=sessions,
            )
        ]

        answer = inquirer.prompt(question)

        if answer:
            session_name = answer["conversation"]
            context = continue_command(convert_title_file(session_name))
            render_footer(COMMANDS_FOOTER)
            return context, "", session_name

        render_footer(COMMANDS_FOOTER)
        return context, "", session_name
    elif prompt[:5] == "/save":
        if prompt[6:].strip():
            session_name = convert_title_file(prompt[6:].strip())
        elif session_name:
            pass
        else:
            print("No session name provided")
            render_footer(COMMANDS_FOOTER)
            return context, "", session_name
        with open(CONVERSATION_PATH / session_name, "w", encoding="utf-8") as file:
            for line in context:
                file.write(f"{line}\n")
        print("=" * 50)
        render_footer(COMMANDS_FOOTER)
        return context, "", session_name
    elif prompt[:5] == "/exit":
        if session_name:
            with open(CONVERSATION_PATH / session_name, "w", encoding="utf-8") as file:
                for line in context:
                    file.write(f"{line}\n")
        elif prompt[6:]:
            with open(
                CONVERSATION_PATH / convert_title_file(prompt[6:]),
                "w",
                encoding="utf-8",
            ) as file:
                for line in context:
                    file.write(f"{line}\n")
        print("\nExit ollama cloud")
        return context, "/exit", session_name
    else:
        context.append({"role": "user", "content": prompt})
        return context, prompt, session_name


async def fetch_data(url: str, model: str, context: list) -> str:
    """
    Send prompts to the Ollama API and display responses.

    Args:
        url: Base URL of the Ollama API
        model: Selected model name
        context: Conversation history

    Returns:
        Full response string
    """

    full_response = ""

    payload = {"model": model, "messages": context, "stream": True}

    async with aiohttp.ClientSession() as session:
        # Start spinner
        spinner_task_handle = asyncio.create_task(spinner_task())

        try:
            async with session.post(
                f"{url}/v1/chat/completions", json=payload, headers=headers
            ) as response:
                if response.status == 200:
                    # Cancel spinner before printing response
                    spinner_task_handle.cancel()
                    try:
                        await spinner_task_handle
                    except asyncio.CancelledError:
                        pass

                    # Clear the spinner line and print response
                    print("\r" + " " * 50 + "\r", end="", flush=True)

                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            data_str = line[6:].strip()  # Remove 'data: ' prefix
                            if data_str == "[DONE]":
                                break

                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_response += content
                                        print(content, end="", flush=True)

                                    reasoning = delta.get("reasoning_content", "")
                                    if reasoning:
                                        print(
                                            f"\033[90m{reasoning}\033[0m",
                                            end="",
                                            flush=True,
                                        )

                                    # Check if stream is done
                                    if delta.get("finish_reason") == "stop":
                                        break
                            except json.JSONDecodeError:
                                print("\033[91mjson decode error\033[0m")
                                continue

                    if full_response:
                        print()

                else:
                    print(f"\nFailed to fetch data: {response.status}")
        except aiohttp.ClientError as e:
            print(f"\nNetwork error: {e}")
        except json.JSONDecodeError as e:
            print(f"\nFailed to parse response: {e}")
        except KeyError as e:
            print(f"\nUnexpected response format: {e}")
        finally:
            # Ensure spinner is cancelled
            if not spinner_task_handle.done():
                spinner_task_handle.cancel()
                try:
                    await spinner_task_handle
                except asyncio.CancelledError:
                    pass

    return full_response


async def main():
    """Main entry point for the Ollama Cloud AI client."""
    print("=" * 50)
    print("  Ollama Cloud AI Client")
    print("=" * 50)

    # Select model
    model = await select_model(URL)

    if not model:
        print("Failed to initialize. Exiting.")
        return

    session_name = ""
    context = []

    print(f"\nConnected to model: {model}")
    print("Type your prompts (/exit to exit)\n")

    render_footer(COMMANDS_FOOTER)

    while True:
        print("=" * 50)

        context, prompt, session_name = await prompt_input(context, session_name)

        if prompt == "/exit":
            break
        if model and prompt:
            full_response = await fetch_data(URL, model, context)
            if full_response:
                context.append({"role": "assistant", "content": full_response})
        elif model and not prompt:
            pass
        else:
            print("Failed to initialize. Exiting.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExit ollama cloud")
