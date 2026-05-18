"""Shared interactive Q&A helpers used by all workflow modules."""

from datetime import datetime

import typer

from ..display import console, C_ACCENT, C_MUTED, C_PRIMARY
from ..jira_client import JiraClient, md_to_adf


_DONE = ";;"


def ask(question: str, hint: str = "") -> str:
    """Collect a single or multiline answer. Type ;; on its own line to finish."""
    console.print()
    console.print(f"  [{C_PRIMARY}]{question}[/{C_PRIMARY}]")
    if hint:
        console.print(f"  [{C_MUTED}]{hint}[/{C_MUTED}]")
    console.print(f"  [{C_MUTED}](;; en línea nueva para terminar)[/{C_MUTED}]")
    lines: list[str] = []
    while True:
        console.print(f"  [{C_ACCENT}]→[/{C_ACCENT}] ", end="")
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip() == _DONE:
            break
        lines.append(line)
    return "\n".join(lines).strip()


def ask_multiline(question: str, hint: str = "") -> str:
    """Alias for ask(). Kept for semantic clarity in workflow code."""
    return ask(question, hint)


def ask_choice(question: str, options: list[tuple[str, str]]) -> int:
    """Show numbered options, return chosen index (1-based)."""
    console.print()
    console.print(f"  [{C_PRIMARY}]{question}[/{C_PRIMARY}]")
    for i, (short, desc) in enumerate(options, 1):
        console.print(f"  [{C_ACCENT}]{i}.[/{C_ACCENT}] {short}")
        if desc:
            console.print(f"     [{C_MUTED}]{desc}[/{C_MUTED}]")
    while True:
        console.print(f"  [{C_ACCENT}]→[/{C_ACCENT}] ", end="")
        try:
            raw = input().strip()
        except (EOFError, KeyboardInterrupt):
            raise typer.Abort()
        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                return idx
        except ValueError:
            pass
        console.print(f"  [{C_MUTED}]Elige un número del 1 al {len(options)}[/{C_MUTED}]")


def _build_section_header(state: str, date_str: str) -> str:
    return f"## {state} — {date_str}"


def append_section(jira: JiraClient, issue_key: str, section_title: str, content: str) -> None:
    """Append a dated ADF section to the Jira ticket description without round-tripping through text."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    new_adf = md_to_adf(f"## {section_title} — {date_str}\n\n{content}")

    current_adf = jira.get_description_adf(issue_key)
    current_content = current_adf.get("content", [])
    separator = [{"type": "rule"}] if current_content else []

    combined = {
        "type": "doc",
        "version": 1,
        "content": current_content + separator + new_adf.get("content", []),
    }
    jira.update_issue(issue_key, {"description": combined})
