"""
Ollama Cloud AI Client - OpenAI Compatible Mode
Interactive model selector with async HTTP requests and spinner
Uses OpenAI /v1/chat/completions API format
"""

import json
import aiohttp
import asyncio
import inquirer
from pathlib import Path
import ast
from typing import Tuple
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
URL = os.getenv("URLS").split(',')[0]
API_KEY = os.getenv("API_KEY")
CONVERSATION_PATH = os.getenv("CONVERSATION_PATH")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

async def spinner_task():
    """Display a loading spinner animation."""
    SPINNER_CHARS = "|/-\\"
    try:
        while True:
            for char in SPINNER_CHARS:
                print(f"\r{char}", end='', flush=True)
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass

def convert_title_file(title: str) -> str:
    return f"{title.replace(' ','_')}.txt"

def continue_command(title: str) -> list:
    with open(fr"{CONVERSATION_PATH}{title}",'r',encoding='utf-8') as file:
        print("=" * 50)
        context = []
        lines = file.readlines()
        for line in lines:
            line_object = ast.literal_eval(line[:-1])
            context.append(line_object)
            if line_object["role"] == "user":
                print(f"> {line_object["content"]}")
            elif line_object["role"] == "assistant":
                print(line_object["content"])
            print("=" * 50)
        return context
    

async def fetch_data(url: str, model: str, context) -> Tuple[str,int]:
    """
    Send prompts to the Ollama API and display responses.
    
    Args:
        url: Base URL of the Ollama API
        model: Selected model name
    """

    full_response = ""
    stream_reasoning = True

    payload = {
        "model": model,
        "messages": context,
        "stream": True
    }

    async with aiohttp.ClientSession() as session:
        # Start spinner
        spinner_task_handle = asyncio.create_task(spinner_task())
        
        try:
            async with session.post(f"{url}/v1/chat/completions", json=payload, headers=headers) as response:
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
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_str = line[6:].strip()  # Remove 'data: ' prefix
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    reasoning = delta.get("reasoning", "")
                                    if reasoning:
                                        print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
                                    else:
                                        if stream_reasoning:
                                            print()
                                        stream_reasoning = False
                                    if content:
                                        full_response += content
                                        print(content, end="", flush=True)
                                    # Check if stream is done
                                    if choices[0].get("finish_reason") == "stop":
                                        print()
                                        break
                            except json.JSONDecodeError:
                                print("json decode error")
                                continue
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

async def main():
    """Main entry point for the Ollama Cloud AI client."""

    session_name = ''
    context = []

    print('=' * 50)
    print("  Ollama Cloud AI Client")
    print('=' * 50)
    
    model = await asyncio.get_event_loop().run_in_executor(
        None, lambda: input("type you model: ")
    )

    print(f"\nConnected to model: {model}")
    print("Type your prompts (/exit to exit)\n")

    while True:
        print('=' * 50)

        prompt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("> ")
        )

        if prompt[:9] == "/continue":
            if prompt[10:]:
                session_name = convert_title_file(prompt[10:])
                context = continue_command(convert_title_file(prompt[10:]))
                continue

            session_list = [item.name for item in Path(CONVERSATION_PATH).iterdir()]
            if not session_list:
                print("No previous conversation")
                continue

            question = [
                inquirer.List(
                    'conversation',
                    message="Select a previous conversation",
                    choices=session_list,
                )
            ]

            answer = inquirer.prompt(question)

            if answer:
                session_name = answer["conversation"]
                context = continue_command(answer["conversation"])
                continue

            print("No selected conversation")
            continue
        elif prompt[:5] == "/save":
            session_name = convert_title_file(prompt[6:])
            with open(fr"{CONVERSATION_PATH}{convert_title_file(prompt[6:])}",'w',encoding='utf-8') as file:
                for line in context:
                    file.write(f'{line}\n')
            continue
        elif prompt[:5] == "/exit":
            if session_name:
                with open(fr"{CONVERSATION_PATH}{session_name}",'w',encoding='utf-8') as file:
                    for line in context:
                        file.write(f'{line}\n')
            elif prompt[6:]:
                with open(fr"{CONVERSATION_PATH}{convert_title_file(prompt[6:])}",'w',encoding='utf-8') as file:
                    for line in context:
                        file.write(f'{line}\n')
            print("\nExit ollama cloud")
            break
        elif prompt[:7] == "/change":
            print("you change url to runpod")
        else:
            context.append({"role":"user","content":prompt})
    
        if model and prompt:
            # Start chat session
            await fetch_data(URL, model, context)
        else:
            print("Failed to initialize. Exiting.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExit ollama cloud")