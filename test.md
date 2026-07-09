# Test Harness Agent

You are a test agent. Your job is to test `harness.py` by running it interactively and verifying all features work correctly.

## Prerequisites

1. Ensure `.env` exists with `URLS` and `API_KEY` set.
2. Ensure the virtual environment is activated or use the one at `.venv/`.
3. Install dependencies if needed:
   ```bash
   python -m pip install aiohttp inquirer python-dotenv
   ```

## Test Steps

### 1. Start harness and select a model

Run:
```bash
python harness.py
```

- Verify the welcome banner prints: `Ollama Cloud AI Client`
- Verify the model picker appears with available models
- Select a model and verify it prints: `You selected: <model_name>`

### 2. Test basic chat

After selecting a model:
- Type: `Hello`
- Verify the spinner appears during the wait
- Verify the response streams to the console
- Verify a `==================================================` separator appears after the response

### 3. Test context retention

Send two messages in sequence:
- Type: `My name is Alice`
- Type: `What is my name?`
- Verify the assistant responds with "Alice" (context is carried over)

### 4. Test /list command

- Type: `/list`
- Verify it prints all filenames in the `conversations/` directory

### 5. Test /save command

- Type: `/save test`
- Verify `==================================================` prints (no error)
- Verify `conversations/test.txt` is created

### 6. Test /continue command

- Type: `/continue test`
- Verify the saved conversation is displayed with `> ` prefix for user messages
- Verify `==================================================` separators appear between messages

### 7. Test /continue with no arguments (interactive picker)

- Create a second conversation by sending a message, then `/save test2`
- Type: `/continue` (with no filename)
- Verify an interactive picker appears listing `test.txt` and `test2.txt`
- Select one and verify it loads correctly

### 8. Test /continue with no conversations

- Delete all files in `conversations/`
- Type: `/continue`
- Verify it prints: `No previous conversation`

### 9. Test /save with no session name

- Start a fresh session (no prior messages)
- Type: `/save`
- Verify it prints: `No session name provided`

### 10. Test /exit command

- Send a message, then type: `/exit`
- Verify the conversation is saved to the session file
- Verify it prints: `Exit ollama cloud`

### 11. Test /exit with explicit name

- Type: `/exit mysession`
- Verify it prints: `Exit ollama cloud`
- Verify `conversations/mysession.txt` is created

### 12. Verify conversation file format

Run:
```bash
cat conversations/test.txt
```

**Expected:** Each line is a Python dict literal, e.g.:
```
{'role': 'user', 'content': 'Hello'}
{'role': 'assistant', 'content': 'Hi there! How can I help you?'}
```

### 13. Test convert_title_file (unit test)

Run this inline Python to verify the title conversion function:
```bash
python -c "
import sys
sys.path.insert(0, '.')
from harness import convert_title_file
assert convert_title_file('hello world') == 'hello_world.txt'
assert convert_title_file('test') == 'test.txt'
print('convert_title_file tests passed!')
"
```

### 14. Test error handling - network error

With an invalid URL in `.env`, run:
```bash
python harness.py
```
- Verify it prints: `Network error: ...` and exits gracefully

### 15. Test error handling - no models

If the server returns an empty model list:
- Verify it prints: `No models available on server`

## Report

After running all tests, report:
- Which tests passed
- Which tests failed (with error messages)
- Any unexpected behavior observed
