import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

anthropic_client = anthropic.Client()
MODEL = "claude-haiku-5-5"
MAX_TURNS = 10

console = Console()  # user-facing only

# Developer monitoring log (see helpers/agent_logger.py). Follow with: tail -f logs/agent.log
LOG_FILE = Path(__file__).parent / "logs" / "agent.log"
LOG_TO_STDERR = os.getenv("AGENT_LOG_STDERR") == "1"
