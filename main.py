import asyncio
import time

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import Header, Input, Footer, Static
from textual.binding import Binding
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

class ErrorMessage(Static):
    def __init__(self, error_message: str):
        super().__init__(f"Error: {error_message}", markup=False)
        self.add_class("error")

class ChatApp(App):
    TITLE = "CyperAgent"
    CSS_PATH = "static/styles.css"
    BINDINGS = [
        ("ctrl+q", "quit", "exit"),
        Binding("escape", "quit_turn", "Quit current turn")
    ]

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self._current_turn = None
        self._turn_seq = 0

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

        if not self._current_turn is None and self._current_turn.is_running:
            return
        
        self._turn_seq += 1        
        prompt = self.query_one("#prompt", Input)
        prompt.value = ""
        prompt.disabled = True
        self._current_turn = self.run_turn(text, self._turn_seq)

    def action_quit_turn(self):
        try:
            self._current_turn.cancel()
        except:
            return False
        return False
            

    @work(exclusive=True)
    async def run_turn(self, text, seq: int):
        
        try:
            transcript = self.query_one("#transcript", VerticalScroll)
            status = self.query_one("#status", Static)
            prompt = self.query_one("#prompt", Input)
    
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
            prompt.disabled = False
            prompt.focus()
            return None
        except asyncio.CancelledError:
            status.update("Messaggio interrotto...")
            raise 
        except Exception as e:
            self.log("Exception", e)
            await transcript.mount(ErrorMessage(e))
            return None
        finally:
            status.update("")
            prompt.disabled = False
            prompt.focus()

if __name__ == "__main__":
    ChatApp(create_engine()).run()