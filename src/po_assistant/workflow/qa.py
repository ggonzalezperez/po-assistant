"""Shared interactive Q&A helpers used by all workflow modules."""

from datetime import datetime

import typer

from ..display import console, C_ACCENT, C_MUTED, C_PRIMARY
from ..jira_client import JiraClient, md_to_adf


def ask(question: str, hint: str = "") -> str:
    """Display a question and return the PO's one-line answer."""
    console.print()
    console.print(f"  [{C_PRIMARY}]{question}[/{C_PRIMARY}]")
    if hint:
        console.print(f"  [{C_MUTED}]{hint}[/{C_MUTED}]")
    console.print(f"  [{C_ACCENT}]→[/{C_ACCENT}] ", end="")
    try:
        return input().strip()
    except (EOFError, KeyboardInterrupt):
        raise typer.Abort()


def ask_multiline(question: str, hint: str = "") -> str:
    """Display a question expecting multiline input; blank line ends input."""
    console.print()
    console.print(f"  [{C_PRIMARY}]{question}[/{C_PRIMARY}]")
    if hint:
        console.print(f"  [{C_MUTED}]{hint}[/{C_MUTED}]")
    console.print(f"  [{C_MUTED}](línea en blanco para terminar)[/{C_MUTED}]")
    lines: list[str] = []
    while True:
        console.print(f"  [{C_ACCENT}]·[/{C_ACCENT}] ", end="")
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines)


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
    """Append a markdown section to the Jira ticket description (cumulative)."""
    issue = jira.get_issue(issue_key)
    current_text = issue.description or ""
    date_str = datetime.now().strftime("%Y-%m-%d")
    header = _build_section_header(section_title, date_str)
    new_section = f"{header}\n\n{content}"
    separator = "\n\n---\n\n"
    full_text = (current_text + separator + new_section) if current_text.strip() else new_section
    jira.update_issue(issue_key, {"description": md_to_adf(full_text)})
