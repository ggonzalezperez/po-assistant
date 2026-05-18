import json
from pathlib import Path

import anthropic
from rich.console import Console

from .config import Config

console = Console()

PROMPTS_DIR = Path(__file__).parent / "prompts"


class AIClient:
    def __init__(self, config: Config):
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = config.claude_model
        self.config = config

    def _load_prompt(self, prompt_file: str) -> str:
        path = PROMPTS_DIR / prompt_file
        if not path.exists():
            raise FileNotFoundError(f"Prompt no encontrado: {path}")
        return path.read_text(encoding="utf-8")

    def call(self, prompt_file: str, variables: dict[str, str], max_tokens: int = 4096) -> str:
        """Load a prompt file, substitute variables, call Claude, return raw text."""
        system_prompt = self._load_prompt(prompt_file)
        for key, value in variables.items():
            system_prompt = system_prompt.replace(f"{{{{{key}}}}}", value)

        with console.status(f"[dim]Consultando Claude ({self.model})…[/dim]", spinner="dots"):
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": variables.get("USER_INPUT", "Procesa el input.")}],
                system=system_prompt,
            )
        return message.content[0].text.strip()

    def call_json(self, prompt_file: str, variables: dict[str, str], max_tokens: int = 4096) -> dict:
        """Like call() but parses the response as JSON."""
        raw = self.call(prompt_file, variables, max_tokens)
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"La IA no devolvió JSON válido.\nRespuesta recibida:\n{raw[:500]}") from e
