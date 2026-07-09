# my-harness

Python scripts for chatting with Ollama-compatible AI backends (local Ollama, RunPod).

## Setup

```bash
python -m pip install -r requirements.txt
```

Set `URLS` (and `API_KEY` for RunPod) in `.env` before running. `URLS` may contain comma-separated URLs — `test_2.py` and `test_model.py` split on `,` and take `[0]`.

## Run

| Script | What it does |
|---|---|
| `ollama-cloud_openai_compatibility.py` | Interactive chat — fetches models via `/v1/models`, streams via `/v1/chat/completions` |
| `ollama-cloud_runpod.py` | RunPod mode — submits job to `/run`, polls `/stream/{job_id}` |
| `model_selector.py` | Standalone `inquirer` model picker (no network call) |
| `spinner.py` | Sync spinner demo — runs forever until Ctrl+C |
| `test_2.py` | Quick chat via `openai` SDK — one-shot |
| `test_3.py` | Conversation file I/O smoke test |
| `test_model.py` | Lists models via `/api/tags` |
| `test_runpod_endpoint.py` | RunPod `/run` + `/stream` smoke test (sync `requests`) |

## Gotchas

- **Never copy paths from `ollama-cloud_openai_compatibility.py`** — it has stale hardcoded Windows paths (`D:\User\Documents\...`). Both main scripts use `Path(__file__).resolve().parent / "conversations"` instead.
- **Conversation files** live in `conversations/` (auto-created). Each line is a Python literal (`ast.literal_eval`), not JSON.
- **No test framework, linter, or formatter.** Scripts run directly.
- **`spinner.py` runs forever** — it's a standalone demo. The async spinners in the main scripts cancel via `asyncio.CancelledError`.
- **`ollama-cloud_runpod.py:157`** references `spinner_task_handle` before it's defined — a latent bug if the `/run` call succeeds but the subsequent polling loop hasn't started yet.
