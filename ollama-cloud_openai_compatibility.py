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
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
URL = os.getenv("URLS")

headers = {
    "Authorization": "Bearer " + os.getenv("API_KEY"),
    "Content-Type": "application/json"
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
                    models = [m['id'] for m in result.get('data', [])]

                    if not models:
                        print("No models available on server")
                        return None

                    question = [
                        inquirer.List(
                            'model',
                            message="Select a model",
                            choices=models,
                        )
                    ]

                    answer = inquirer.prompt(question)

                    if answer:
                        selected_model = answer['model']
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
                print(f"\r{char}", end='', flush=True)
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass

def convert_title_file(title: str) -> str:
    return f"{title.replace(' ','_')}.txt"

def continue_command(title: str) -> list:
    with open(fr"D:\User\Documents\coding\python\cloud_ai\conversation\{title}",'r',encoding='utf-8') as file:
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
    

async def fetch_data(url: str, model: str) -> None:
    """
    Send prompts to the Ollama API and display responses.
    
    Args:
        url: Base URL of the Ollama API
        model: Selected model name
    """

    session_name = ''
    context = []

    if not model:
        print("No model selected. Exiting.")
        return

    print(f"\nConnected to model: {model}")
    print("Type your prompts (/exit to exit)\n")

    while True:
        full_response = ""
        stream_reasoning = True

        # Use asyncio-compatible input
        prompt = await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("> ")
        )

        if prompt == "/list":
            for item in Path(r'D:\User\Documents\coding\python\cloud_ai\conversation').iterdir():
                print(item.name)
            print()
            continue
        elif prompt[:9] == "/continue":
            if prompt[10:]:
                session_name = convert_title_file(prompt[10:])
                context = continue_command(convert_title_file(prompt[10:]))
                continue

            session_list = [item.name for item in Path(r'D:\User\Documents\coding\python\cloud_ai\conversation').iterdir()]
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
            with open(fr"D:\User\Documents\coding\python\cloud_ai\conversation\{convert_title_file(prompt[6:])}",'w',encoding='utf-8') as file:
                for line in context:
                    file.write(f'{line}\n')
            print("=" * 50)
            continue
        elif prompt[:5] == "/exit":
            if session_name:
                with open(fr"D:\User\Documents\coding\python\cloud_ai\conversation\{session_name}",'w',encoding='utf-8') as file:
                    for line in context:
                        file.write(f'{line}\n')
            elif prompt[6:]:
                with open(fr"D:\User\Documents\coding\python\cloud_ai\conversation\{convert_title_file(prompt[6:])}",'w',encoding='utf-8') as file:
                    for line in context:
                        file.write(f'{line}\n')
            print("\nExit ollama cloud")
            return
        else:
            context.append({"role":"user","content":prompt})

        print('=' * 50)

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
                                        if content:
                                            full_response += content
                                            print(content, end="", flush=True)

                                        try:
                                            reasoning = delta.get("reasoning", "")
                                            print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
                                        except:
                                            if stream_reasoning:
                                                print()
                                            stream_reasoning = False
                                            pass

                                        # Check if stream is done
                                        if delta.get("finish_reason") == "stop":
                                            print(f"\n{'=' * 50}")
                                            break
                                except json.JSONDecodeError:
                                    print("json decode error")
                                    continue

                        context.append({"role":"assistant","content":full_response})

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
    print('=' * 50)
    print("  Ollama Cloud AI Client")
    print('=' * 50)
    
    # Select model
    model = await select_model(URL)
    
    if model:
        # Start chat session
        await fetch_data(URL, model)
    else:
        print("Failed to initialize. Exiting.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExit ollama cloud")