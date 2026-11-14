import anthropic
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

anthropic_client = anthropic.Client()
MODEL = "claude-haiku-5-5"
MAX_TURNS = 10

console = Console()
