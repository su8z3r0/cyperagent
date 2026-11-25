from textual.app import App, ComposeResult
from textual.widgets import Header, RichLog, Input, Footer
from textual.containers import Container, Horizontal

class ChatApp(App):
    TITLE = "chatui"
    SUB_TITLE = "ChatGPT directly in your terminal"
    CSS_PATH = "static/styles.css"

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog()
        yield Input()
        yield Footer()
        

app = ChatApp()
app.run()