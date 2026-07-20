"""
Ollama Cloud AI Client - Textual TUI
Interactive model selector with async HTTP requests and spinner
Uses OpenAI /v1/chat/completions API format
"""

import ast
import asyncio
import json
import os
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from textual import on
from textual.app import App, ComposeResult, Screen
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Select,
)

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

COMMANDS_FOOTER = "/list      /continue      /save      /exit"


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


def continue_command(title: str) -> list:
    with open(CONVERSATION_PATH / title, "r", encoding="utf-8") as file:
        context = []
        lines = file.readlines()
        for line in lines:
            line_object = ast.literal_eval(line.rstrip("\n"))
            context.append(line_object)
            if line_object["role"] == "user":
                print(f"> {line_object['content']}")
            elif line_object["role"] == "assistant":
                print(line_object['content'])
            print("=" * 50)
        return context


class SessionPickerScreen(ModalScreen):
    """Modal screen for picking a session to continue."""

    CSS = """
    SessionPickerScreen {
        align: center middle;
        width: 60;
        height: 20;
        background: $surface;
        border: solid $primary;
    }

    #session-list {
        margin: 1;
    }
    """

    def __init__(self, sessions: list[str]) -> None:
        super().__init__()
        self.sessions = sessions
        self.selected_session: str | None = None

    def compose(self) -> ComposeResult:
        yield Label("Select a previous conversation:")
        yield Select(
            [(s, s) for s in self.sessions],
            id="session-select",
        )

    @on(Select.Changed)
    def selection_changed(self, event: Select.Changed) -> None:
        self.selected_session = event.value

    @on(Input.Submitted)
    def submit(self) -> None:
        if self.selected_session:
            self.dismiss(self.selected_session)


class SelectScreen(ModalScreen):
    """Screen for selecting a model."""

    CSS = """
    SelectScreen {
        align: center middle;
        width: 60;
        height: 15;
        background: $surface;
        border: solid $primary;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.selected_model: str | None = None

    def compose(self) -> ComposeResult:
        yield Label("Loading models...")
        yield LoadingIndicator()
        yield Button("Select", id="select-submit")

    async def on_mount(self) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{URL}/v1/models", headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        models = [m["id"] for m in result.get("data", [])]

                        if not models:
                            self.query_one(Label).update(
                                "No models available on server"
                            )
                            return

                        self.query_one(Label).remove()
                        self.query_one(LoadingIndicator).remove()
                        select = Select(
                            [(m, m) for m in models],
                            id="model-select",
                        )
                        self.mount(select)
                        select.focus()
                    else:
                        self.query_one(Label).update(
                            f"Failed to fetch model data: {response.status}"
                        )
        except Exception as e:
            self.query_one(Label).update(f"Error: {e}")

    @on(Select.Changed)
    def selection_changed(self, event: Select.Changed) -> None:
        self.selected_model = event.value

    @on(Button.Pressed)
    def submit(self) -> None:
        if self.selected_model:
            self.dismiss(self.selected_model)

    def on_key(self, event) -> None:
        if event.key == "enter" and self.selected_model:
            self.dismiss(self.selected_model)


class MainScreen(Screen):
    """Main chat screen."""

    CSS = """
    MainScreen {
        layout: vertical;
    }

    #conversation-log {
        height: 1fr;
        overflow-y: auto;
        border: none;
    }

    #input-bar {
        height: 3;
        layout: horizontal;
    }

    #prompt-label {
        width: 3;
        content-align: center middle;
        text-style: bold;
    }

    #user-input {
        width: 1fr;
    }

    #status-line {
        height: 1;
        background: $boost;
        color: $text;
        content-align: center middle;
    }

    #spinner-container {
        height: 1;
        display: none;
        content-align: center middle;
    }
    """

    BINDINGS = [
        ("up", "history_up", "Prev"),
        ("down", "history_down", "Next"),
    ]

    def __init__(self, model: str) -> None:
        super().__init__()
        self.model = model
        self.messages: list[dict] = []
        self.session_name: str = ""
        self.input_history: list[str] = []
        self._history_index: int = -1

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("", id="conversation-log")
        with Container(id="input-bar"):
            yield Label(">", id="prompt-label")
            yield Input(
                id="user-input",
            )
        yield Label("", id="status-line")
        yield Container(LoadingIndicator(), id="spinner-container")
        yield Footer()

    def on_mount(self) -> None:
        self.update_status()

    def update_status(self) -> None:
        status_text = f"Model: {self.model}  |  {COMMANDS_FOOTER}"
        self.query_one("#status-line", Label).update(status_text)

    def set_loading(self, loading: bool) -> None:
        spinner_container = self.query_one("#spinner-container", Container)
        spinner_container.display = loading

    def append_message(self, role: str, content: str) -> None:
        log = self.query_one("#conversation-log", Label)
        prefix = "> " if role == "user" else ""
        new_text = log.text + f"\n{prefix}{content}\n{'=' * 50}\n"
        log.update(new_text)

    def append_streaming(self, content: str) -> None:
        log = self.query_one("#conversation-log", Label)
        log.update(log.text + content)

    async def handle_input(self, prompt: str) -> None:
        if prompt == "/list":
            sessions = get_sorted_sessions()
            self.append_message("system", format_sessions(sessions))
            return

        if prompt[:9] == "/continue":
            conv_name = prompt[9:].strip()
            if conv_name:
                session_name = convert_title_file(conv_name)
                self.messages = continue_command(session_name)
                self.session_name = session_name
                self.append_message("system", f"Continued session: {session_name}")
                self.update_status()
                return

            sessions = get_sorted_sessions()
            if not sessions:
                self.append_message("system", "No previous conversation")
                return

            picker = SessionPickerScreen(sessions)
            session = await self.app.push_screen_modal(picker)  # type: ignore[attr-defined]
            if session:
                session_name = convert_title_file(session)
                self.messages = continue_command(session_name)
                self.session_name = session_name
                self.append_message("system", f"Continued session: {session_name}")
                self.update_status()
            return

        if prompt[:5] == "/save":
            save_name = prompt[6:].strip()
            if save_name:
                self.session_name = convert_title_file(save_name)
            elif not self.session_name:
                self.append_message("system", "No session name provided")
                return
            with open(
                CONVERSATION_PATH / self.session_name, "w", encoding="utf-8"
            ) as file:
                for line in self.messages:
                    file.write(f"{line}\n")
            self.append_message("system", f"Saved session: {self.session_name}")
            self.update_status()
            return

        if prompt[:5] == "/exit":
            if self.session_name:
                with open(
                    CONVERSATION_PATH / self.session_name, "w", encoding="utf-8"
                ) as file:
                    for line in self.messages:
                        file.write(f"{line}\n")
            elif prompt[6:]:
                with open(
                    CONVERSATION_PATH / convert_title_file(prompt[6:]),
                    "w",
                    encoding="utf-8",
                ) as file:
                    for line in self.messages:
                        file.write(f"{line}\n")
            self.app.exit()  # type: ignore[attr-defined]
            return

        # Normal message
        self.messages.append({"role": "user", "content": prompt})
        self.append_message("user", prompt)
        self.input_history.append(prompt)

        await self.send_to_api()

    async def send_to_api(self) -> None:
        self.set_loading(True)
        full_response = ""

        payload = {"model": self.model, "messages": self.messages, "stream": True}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{URL}/v1/chat/completions", json=payload, headers=headers
                ) as response:
                    if response.status == 200:
                        self.set_loading(False)
                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
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
                                            self.append_streaming(content)
                                except json.JSONDecodeError:
                                    continue

                        if full_response:
                            self.messages.append(
                                {"role": "assistant", "content": full_response}
                            )
                    else:
                        self.set_loading(False)
                        self.append_message("system", f"Failed: {response.status}")
        except Exception as e:
            self.set_loading(False)
            self.append_message("system", f"Error: {e}")

    @on(Input.Submitted)
    def handle_submit(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if prompt:
            self.set_loading(True)
            asyncio.create_task(self.handle_input(prompt))
            event.input.clear()

    def action_history_up(self) -> None:
        if not self.input_history:
            return
        if self._history_index == -1:
            self._history_index = len(self.input_history) - 1
        elif self._history_index > 0:
            self._history_index -= 1
        self.query_one("#user-input", Input).value = self.input_history[
            self._history_index
        ]

    def action_history_down(self) -> None:
        if self._history_index == -1:
            return
        if self._history_index < len(self.input_history) - 1:
            self._history_index += 1
            self.query_one("#user-input", Input).value = self.input_history[
                self._history_index
            ]
        else:
            self._history_index = -1
            self.query_one("#user-input", Input).value = ""


class HarnessApp(App):
    """Main application."""

    CSS = """
    Screen {
        layout: vertical;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(SelectScreen(), self.on_model_selected)

    def on_model_selected(self, model: str) -> None:
        """Called when SelectScreen is dismissed with a model."""
        if not model:
            self.exit()
            return

        self.push_screen(MainScreen(model))


if __name__ == "__main__":
    app = HarnessApp()
    app.run()
