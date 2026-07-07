# my-harness

Python scripts for interacting with Ollama-compatible AI backends (local Ollama, RunPod).

## Run

```bash
python -m pip install aiohttp inquirer python-dotenv
```

Set `.env` with `URLS` and `API_KEY` before running.

## Files

| File | Purpose |
|---|---|
| `ollama-cloud_openai_compatibility.py` | Direct OpenAI `/v1/chat/completions` streaming client (async aiohttp) |
| `ollama-cloud_runpod.py` | RunPod job-submit-then-stream client (`/run` + `/stream/{job_id}`) |
| `model_selector.py` | Standalone `inquirer` model picker |
| `spinner.py` | Sync spinner utility (standalone demo) |
| `test_*.py` | One-off scripts — not a test suite |

## Gotchas

- `ollama-cloud_openai_compatibility.py:94,138-148,172,179,183` — stale Windows paths (`D:\User\Documents\...`). The RunPod version uses `Path(__file__).resolve().parent / "conversations"` instead. Do not copy the hardcoded paths from the OpenAI-compatible file.
- `URLS` env var may contain comma-separated URLs; `test_2.py` and `test_model.py` split on `,` and take index `[0]`.
- Conversation files are stored in `conversations/` (created automatically by `ollama-cloud_runpod.py`). Each line is a Python literal (`ast.literal_eval`), not JSON.
- No test framework, linter, or formatter configured. Run scripts directly.
- `spinner.py` runs forever until Ctrl+C; it is a standalone demo, not used by the main apps (which cancel their async spinner via `asyncio.CancelledError`).
