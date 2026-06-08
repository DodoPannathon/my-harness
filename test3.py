import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
api_key = os.getenv('API_KEY')
base_path = Path(__file__).resolve().parent
conversation_path = base_path / "conversations"

if not conversation_path.exists():
 print("creat new conversations dir")
 conversation_path.mkdir()

if (conversation_path / "test.txt").exists():
    test = "test.txt"
    with open(conversation_path / test, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        print(lines)
else:
    print("file does not exist")