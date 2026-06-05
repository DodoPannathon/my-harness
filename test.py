# import requests

# headers = {
#     "Authorization": "Bearer api_key",
#     "Content-Type": "application/json"
# }
# payload = {
#     "input": {
#         "openai_route": "/v1/chat/completions",
#         "openai_input": {
#             "model": "qwen3.6:35b-a3b",
#             "messages": [
#                 {"role": "user", "content": "Why is the sky blue?"}
#             ]
#         }
#     }
# }

# response = requests.post(url, json=payload, headers=headers)
# print(response.json())

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("URLS").split(',')[1]
headers = {
    "Authorization": f"Bearer {os.getenv("API_KEY")}",
    "Content-Type": "application/json"
}

payload = {
    "input": {
        "openai_route": "/v1/chat/completions",
        "openai_input": {
            "model": "qwen3.6:35b-a3b",
            "messages": [
                {"role": "user", "content": "Why is the sky blue?"}
            ],
            "stream": True
        }
    }
}

# Submit job
response = requests.post(f"{url}/run", json=payload, headers=headers)
job_id = response.json()["id"]
print(f"Job ID: {job_id}")

stream_reasoning = True

while True:
    stream_response = requests.get(f"{url}/stream/{job_id}", headers=headers)
    data = stream_response.json()
    if not data.get("stream",[]):
        print(data)

    for item in data.get("stream", []):
        raw = item.get("output", "")
        if raw == "data: [DONE]":
            break
        json_str = raw[6:-2].strip()
        chunk = json.loads(json_str)
        delta = chunk["choices"][0]["delta"]
        try:
            reasoning = delta["reasoning"]
            if reasoning:
                print(f"\033[90m{reasoning}\033[0m", end="", flush=True)
        except:
            if stream_reasoning:
                print()
            stream_reasoning = False
            pass
        content = delta["content"]
        if content:
            print(content, end="", flush=True)

    # Stop when job is done
    if data.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
        break