import json
import re
from datetime import datetime, timezone
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth
from rich.console import Console

from .config import Config
from .models import JiraIssue, POEstado

console = Console()


class JiraError(Exception):
    pass


class JiraClient:
    def __init__(self, config: Config):
        self.base = config.jira_base_url
        self.auth = HTTPBasicAuth(config.jira_email, config.jira_api_token)
        self.headers = {"Accept": "application/json", "Content-Type": "application/json"}
        self.config = config
        self.dry_run = config.dry_run

    # ── Internal HTTP ────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = requests.get(
            f"{self.base}/rest/api/3{path}",
            auth=self.auth, headers=self.headers, params=params, timeout=30
        )
        self._raise(resp)
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        if self.dry_run:
            console.print(f"[dim][DRY_RUN] POST {path}[/dim]")
            return {"id": "DRY-0", "key": f"{self.config.jira_po_project_key}-DRY"}
        resp = requests.post(
            f"{self.base}/rest/api/3{path}",
            auth=self.auth, headers=self.headers,
            data=json.dumps(data), timeout=30,
        )
        self._raise(resp)
        return resp.json() if resp.text else {}

    def _put(self, path: str, data: dict) -> None:
        if self.dry_run:
            console.print(f"[dim][DRY_RUN] PUT {path}[/dim]")
            return
        resp = requests.put(
            f"{self.base}/rest/api/3{path}",
            auth=self.auth, headers=self.headers,
            data=json.dumps(data), timeout=30,
        )
        self._raise(resp)

    @staticmethod
    def _raise(resp: requests.Response) -> None:
        if not resp.ok:
            try:
                detail = resp.json()
                msgs = detail.get("errorMessages", []) or list(detail.get("errors", {}).values())
                msg = "; ".join(msgs) if msgs else resp.text[:200]
            except Exception:
                msg = resp.text[:200]
            raise JiraError(f"HTTP {resp.status_code}: {msg}")

    # ── Auth / Project ───────────────────────────────────────────────────────

    def get_myself(self) -> dict:
        return self._get("/myself")

    def create_project(self, key: str, name: str, account_id: str) -> dict:
        return self._post("/project", {
            "key": key,
            "name": name,
            "projectTypeKey": "software",
            "description": "Flujo Product Owner — Flexicar",
            "leadAccountId": account_id,
            "assigneeType": "UNASSIGNED",
        })

    def project_exists(self, key: str) -> bool:
        try:
            self._get(f"/project/{key}")
            return True
        except JiraError:
            return False

    # ── Custom Fields ────────────────────────────────────────────────────────

    def create_text_field(self, name: str, description: str = "") -> dict:
        return self._post("/field", {
            "name": name,
            "description": description,
            "type": "com.atlassian.jira.plugin.system.customfieldtypes:textfield",
            "searcherKey": "com.atlassian.jira.plugin.system.customfieldtypes:textsearcher",
        })

    def create_number_field(self, name: str, description: str = "") -> dict:
        return self._post("/field", {
            "name": name,
            "description": description,
            "type": "com.atlassian.jira.plugin.system.customfieldtypes:float",
            "searcherKey": "com.atlassian.jira.plugin.system.customfieldtypes:exactnumber",
        })

    def get_all_fields(self) -> list[dict]:
        return self._get("/field")

    # ── Issues ───────────────────────────────────────────────────────────────

    def create_issue(
        self,
        summary: str,
        description_md: str,
        issue_type: str = "Story",
        labels: list[str] | None = None,
        extra_fields: dict | None = None,
    ) -> dict:
        fields: dict = {
            "project": {"key": self.config.jira_po_project_key},
            "summary": summary,
            "description": md_to_adf(description_md),
            "issuetype": {"name": issue_type},
        }
        if labels:
            fields["labels"] = labels
        if extra_fields:
            fields.update(extra_fields)
        return self._post("/issue", {"fields": fields})

    def update_issue(self, issue_key: str, fields: dict) -> None:
        self._put(f"/issue/{issue_key}", {"fields": fields})

    def update_labels(self, issue_key: str, new_labels: list[str]) -> None:
        self._put(f"/issue/{issue_key}", {"fields": {"labels": new_labels}})

    def transition_po_state(self, issue_key: str, new_estado: POEstado) -> None:
        """Replace any existing po-* label with the new state label."""
        issue = self.get_issue(issue_key)
        labels = [l for l in issue.labels if not l.startswith("po-")]
        labels.append(new_estado.value)
        self.update_labels(issue_key, labels)

    def add_comment(self, issue_key: str, text_md: str) -> dict:
        return self._post(f"/issue/{issue_key}/comment", {"body": md_to_adf(text_md)})

    def get_issue(self, issue_key: str) -> JiraIssue:
        raw = self._get(f"/issue/{issue_key}")
        f = raw["fields"]
        description = adf_to_text(f.get("description") or {})
        return JiraIssue(
            key=raw["key"],
            summary=f.get("summary", ""),
            description=description,
            status=f.get("status", {}).get("name", ""),
            labels=f.get("labels", []),
            assignee=(f.get("assignee") or {}).get("displayName"),
            created=f.get("created", ""),
            updated=f.get("updated", ""),
            custom_fields={
                k: v for k, v in f.items()
                if k.startswith("customfield_") and v is not None
            },
        )

    def search_issues(self, jql: str, max_results: int = 100) -> list[JiraIssue]:
        data = self._get("/search", params={"jql": jql, "maxResults": max_results})
        return [self.get_issue(i["key"]) for i in data.get("issues", [])]

    def get_project_issues(self) -> list[JiraIssue]:
        jql = f"project = {self.config.jira_po_project_key} ORDER BY created DESC"
        return self.search_issues(jql)


# ── ADF helpers ──────────────────────────────────────────────────────────────

def md_to_adf(text: str) -> dict:
    """Convert simplified markdown to Atlassian Document Format (ADF)."""
    content: list[dict] = []
    lines = text.split("\n")
    i = 0
    bullet_buffer: list[dict] = []

    def flush_bullets() -> None:
        if bullet_buffer:
            content.append({"type": "bulletList", "content": list(bullet_buffer)})
            bullet_buffer.clear()

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.startswith("```"):
            flush_bullets()
            lang = line[3:].strip() or "text"
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            content.append({
                "type": "codeBlock",
                "attrs": {"language": lang},
                "content": [{"type": "text", "text": "\n".join(code_lines)}],
            })

        elif line.startswith("## "):
            flush_bullets()
            content.append({
                "type": "heading", "attrs": {"level": 2},
                "content": [{"type": "text", "text": line[3:].strip()}],
            })

        elif line.startswith("### "):
            flush_bullets()
            content.append({
                "type": "heading", "attrs": {"level": 3},
                "content": [{"type": "text", "text": line[4:].strip()}],
            })

        elif line.startswith("- "):
            bullet_buffer.append({
                "type": "listItem",
                "content": [{"type": "paragraph", "content": _inline(line[2:])}],
            })

        elif line.strip() == "---":
            flush_bullets()
            content.append({"type": "rule"})

        elif line.strip():
            flush_bullets()
            content.append({"type": "paragraph", "content": _inline(line)})

        else:
            flush_bullets()

        i += 1

    flush_bullets()
    return {"type": "doc", "version": 1, "content": content or [{"type": "paragraph", "content": []}]}


def _inline(text: str) -> list[dict]:
    """Convert inline markdown (bold, plain) to ADF inline nodes."""
    nodes: list[dict] = []
    # Split on **bold**
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            nodes.append({"type": "text", "text": part[2:-2], "marks": [{"type": "strong"}]})
        elif part:
            nodes.append({"type": "text", "text": part})
    return nodes or [{"type": "text", "text": ""}]


def adf_to_text(adf: dict) -> str:
    """Extract plain text from ADF for feeding into prompts."""
    if not adf:
        return ""
    parts: list[str] = []

    def walk(node: dict) -> None:
        t = node.get("type", "")
        if t == "text":
            parts.append(node.get("text", ""))
        elif t == "hardBreak":
            parts.append("\n")
        elif t in ("paragraph", "heading", "listItem", "bulletList", "orderedList",
                   "blockquote", "doc", "panel", "codeBlock"):
            for child in node.get("content", []):
                walk(child)
            if t in ("paragraph", "heading", "listItem", "codeBlock"):
                parts.append("\n")
        else:
            for child in node.get("content", []):
                walk(child)

    walk(adf)
    return "".join(parts).strip()
