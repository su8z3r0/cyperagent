import time

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Header, RichLog, Input, Footer, Static
from textual.containers import VerticalScroll
from engine import create_engine

class UserMessage(Static):
    def __init__(self, text: str):
        super().__init__(f"you › {text}", markup=False)
        self.add_class("user")

class AssistantMessage(Static):
    def __init__(self):
        super().__init__("", markup=False)
        self.add_class("assistant")
        self._buf = ""

    def add_token(self, token: str):
        self._buf += token
        self.update(self._buf)

    def text(self) -> str:
        return self._buf

class ChatApp(App):
    TITLE = "CyperAgent"
    CSS_PATH = "static/styles.css"
    BINDINGS = [("ctrl+q", "quit", "exit")]

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="transcript")
        yield Static("", id="status")
        yield Input(id="prompt")
        yield Footer()

    def on_mount(self):
        self.query_one('#prompt', Input).focus()

    def on_input_submitted(self, event):
        text = event.value.strip()
        if not text:
            return
        prompt = self.query_one("#prompt", Input)
        prompt.value = ""
        prompt.disabled = True
        self.run_turn(text)
            

    @work(exclusive=True)
    async def run_turn(self, text):
        transcript = self.query_one("#transcript", VerticalScroll)
        status = self.query_one("#status", Static)

        transcript = self.query_one("#transcript", VerticalScroll)
        await transcript.mount(UserMessage(text))
        assistant = AssistantMessage()
        await transcript.mount(assistant)

        status.update("✻ Thinking…")
        last = 0.0
        async for token in self.engine.stream_turn(text):
            assistant.add_token(token)
            status.update("")
            now = time.monotonic()
            if now - last > 0.06:
                last = now
                if transcript.is_vertical_scroll_end:
                    transcript.scroll_end(animate=False)

        if transcript.is_vertical_scroll_end:
            transcript.scroll_end(animate=False)
        status.update("")
        prompt = self.query_one("#prompt", Input)
        prompt.disabled = False
        prompt.focus()

if __name__ == "__main__":
    ChatApp(create_engine()).run()