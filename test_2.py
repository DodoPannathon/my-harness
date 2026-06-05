from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    base_url=f"{os.getenv("URLS").split(',')[0]}/v1",
    api_key=os.getenv("API_KEY")
)

response = client.chat.completions.create(
    model="qwen3.6:35b-a3b",
    messages=[
        {"role": "user", "content": "Why is the sky blue?"}
    ]
)

print(response.choices[0].message.content)