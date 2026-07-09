import asyncio
import os

import aiohttp
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("URLS")
API_KEY = os.getenv("API_KEY")
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


async def fatch_data():
    prompt = input("> ")
    print()

    payload = {
        "model": "qwen3.6-35b-a3b",
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{URL}/v1/chat/completions", json=payload, headers=headers
        ) as response:
            async for line in response.content:
                line = line.decode("utf-8").strip()
                print(line)


if __name__ == "__main__":
    asyncio.run(fatch_data())
