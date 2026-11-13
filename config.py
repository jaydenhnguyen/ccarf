import anthropic
from dotenv import load_dotenv

load_dotenv()

anthropic_client = anthropic.Client()
MODEL = "claude-haiku-5-5"
MAX_TURNS = 10
