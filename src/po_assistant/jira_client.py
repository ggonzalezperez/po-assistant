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

    def _resolve_issue_type(self, preferred: str) -> dict:
        """Return issuetype field value: use preferred name if available, else first type."""
        try:
            types = self._get(f"/issue/createmeta/{self.config.jira_po_project_key}/issuetypes")
            available = types.get("issueTypes", [])
            for t in available:
                if t.get("name", "").lower() == preferred.lower():
                    return {"id": t["id"]}
            if available:
                return {"id": available[0]["id"]}
        except JiraError:
            pass
        return {"name": preferred}

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
            "issuetype": self._resolve_issue_type(issue_type),
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

    def get_transitions(self, issue_key: str) -> list[dict]:
        """Return available workflow transitions for an issue."""
        return self._get(f"/issue/{issue_key}/transitions").get("transitions", [])

    def apply_transition(self, issue_key: str, transition_name: str) -> bool:
        """Apply a transition by name. Returns True if applied."""
        if self.dry_run:
            return True
        for t in self.get_transitions(issue_key):
            if t.get("to", {}).get("name", "").upper() == transition_name.upper():
                self._post(f"/issue/{issue_key}/transitions", {"transition": {"id": t["id"]}})
                return True
        return False

    def transition_po_state(self, issue_key: str, new_estado: POEstado) -> None:
        """Transition issue to new PO state via Jira workflow + update label."""
        # Real Jira status transition (works when PO workflow is active)
        self.apply_transition(issue_key, new_estado.display)
        # Also sync po-* label (used by CLI dashboard and quick filters)
        issue = self.get_issue(issue_key)
        labels = [lbl for lbl in issue.labels if not lbl.startswith("po-")]
        labels.append(new_estado.value)
        self.update_labels(issue_key, labels)

    def find_user_by_name(self, query: str) -> str | None:
        """Search Jira users by display name or email. Returns accountId or None."""
        try:
            results = self._get("/user/search", params={"query": query, "maxResults": 5})
            if results:
                return results[0]["accountId"]
        except JiraError:
            pass
        return None

    def assign_issue(self, issue_key: str, account_id: str) -> None:
        """Assign an issue to a user by accountId."""
        self._put(f"/issue/{issue_key}/assignee", {"accountId": account_id})

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
        data = self._get("/search/jql", params={
            "jql": jql,
            "maxResults": max_results,
            "fields": "summary,status,labels,assignee,created,updated,description",
        })
        return [self.get_issue(i.get("key") or i["id"]) for i in data.get("issues", [])]

    def get_project_issues(self) -> list[JiraIssue]:
        jql = f"project = {self.config.jira_po_project_key} ORDER BY created DESC"
        return self.search_issues(jql)

    # ── Agile (Boards) ───────────────────────────────────────────────────────

    def _get_agile(self, path: str, params: dict | None = None) -> dict:
        resp = requests.get(
            f"{self.base}/rest/agile/1.0{path}",
            auth=self.auth, headers=self.headers, params=params, timeout=30,
        )
        self._raise(resp)
        return resp.json()

    def _post_agile(self, path: str, data: dict) -> dict:
        if self.dry_run:
            console.print(f"[dim][DRY_RUN] POST agile{path}[/dim]")
            return {"id": 0}
        resp = requests.post(
            f"{self.base}/rest/agile/1.0{path}",
            auth=self.auth, headers=self.headers,
            data=json.dumps(data), timeout=30,
        )
        self._raise(resp)
        return resp.json() if resp.text else {}

    def get_board(self, project_key: str) -> int:
        """Return ID of first Kanban board for the project, or 0 if none."""
        try:
            data = self._get_agile("/board", {"projectKeyOrId": project_key, "type": "kanban"})
            values = data.get("values", [])
            if values:
                return int(values[0]["id"])
        except JiraError:
            pass
        return 0

    def create_filter(self, name: str, jql: str) -> str:
        """Create a saved JQL filter. Returns filter ID."""
        data = self._post("/filter", {
            "name": name,
            "jql": jql,
            "favourite": False,
        })
        return str(data.get("id", ""))

    def create_board(self, name: str, project_key: str) -> int:
        """Create a Kanban board backed by a saved filter. Returns board ID."""
        filter_id = self.create_filter(
            name,
            f"project = {project_key} ORDER BY created DESC",
        )
        data = self._post_agile("/board", {
            "name": name,
            "type": "kanban",
            "filterId": filter_id,
        })
        return int(data.get("id", 0))

    def create_quick_filter(self, board_id: int, name: str, query: str) -> None:
        """Add a quick filter to a board (best-effort)."""
        try:
            self._post_agile(f"/board/{board_id}/quickfilter", {"name": name, "query": query})
        except JiraError:
            pass

    def create_component(self, project_key: str, name: str, description: str = "") -> dict:
        """Create a project component (used as PO team labels)."""
        return self._post("/component", {
            "name": name,
            "description": description,
            "project": project_key,
        })

    # ── Workflow setup ───────────────────────────────────────────────────────

    _PO_STATUSES = [
        ("INTAKE",        "TODO"),
        ("TRIAGE",        "TODO"),
        ("DISCOVERY",     "IN_PROGRESS"),
        ("DEFINICION",    "IN_PROGRESS"),
        ("SIGN-OFF SH",   "IN_PROGRESS"),
        ("DOR GATE",      "IN_PROGRESS"),
        ("HANDSHAKE",     "IN_PROGRESS"),
        ("EN DESARROLLO", "IN_PROGRESS"),
        ("UAT",           "IN_PROGRESS"),
        ("RELEASE",       "DONE"),
    ]

    def get_or_create_po_statuses(self) -> dict[str, str]:
        """Ensure the 10 PO statuses exist globally. Returns {name: id}."""
        try:
            all_statuses = self._get("/status")   # GET /rest/api/3/status
            existing = {s["name"]: s["id"] for s in all_statuses}
        except JiraError:
            existing = {}

        to_create = [
            {"name": n, "statusCategory": cat, "description": ""}
            for n, cat in self._PO_STATUSES
            if n not in existing
        ]
        if to_create:
            created = self._post("/statuses", {   # POST /rest/api/3/statuses
                "statuses": to_create,
                "scope": {"type": "GLOBAL"},
            })
            for s in (created if isinstance(created, list) else []):
                existing[s["name"]] = s["id"]

        return {n: existing[n] for n, _ in self._PO_STATUSES if n in existing}

    def get_project_scheme_id(self, project_id: str) -> int:
        """Return the workflow scheme ID for a project."""
        resp = requests.get(
            f"{self.base}/rest/api/2/workflowscheme/project",
            auth=self.auth, headers=self.headers,
            params={"projectId": project_id}, timeout=30,
        )
        self._raise(resp)
        values = resp.json().get("values", [])
        if values:
            return int(values[0]["workflowScheme"]["id"])
        raise JiraError("Workflow scheme not found for project")

    def po_workflow_exists(self) -> bool:
        """Check whether PO Workflow — Flexicar already exists."""
        try:
            resp = requests.get(
                f"{self.base}/rest/api/3/workflows/search",
                auth=self.auth, headers=self.headers,
                params={"queryString": "PO Workflow"}, timeout=30,
            )
            if resp.ok:
                for wf in resp.json().get("values", []):
                    if "PO Workflow" in wf.get("name", ""):
                        return True
        except Exception:
            pass
        return False

    def create_po_workflow(self, status_ids: dict[str, str]) -> str:
        """Create the PO workflow with 10 statuses and global transitions. Returns workflow name."""
        statuses_list = [
            {"statusReference": status_ids[n], "layout": {"x": float(i * 160), "y": 0.0}, "properties": {}}
            for i, (n, _) in enumerate(self._PO_STATUSES)
        ]
        top_statuses = [
            {"id": status_ids[n], "name": n, "statusCategory": cat,
             "statusReference": status_ids[n], "description": "", "scope": {"type": "GLOBAL"}}
            for n, cat in self._PO_STATUSES
        ]
        transitions = [
            {"id": "1", "name": "Crear", "description": "", "toStatusReference": status_ids["INTAKE"],
             "type": "INITIAL", "links": [], "actions": [], "validators": [], "triggers": [], "properties": {}}
        ]
        for i, (name, _) in enumerate(self._PO_STATUSES):
            transitions.append({
                "id": str(10 + i * 10), "name": name, "description": "",
                "toStatusReference": status_ids[name], "type": "GLOBAL",
                "links": [], "actions": [], "validators": [], "triggers": [], "properties": {}
            })

        resp = requests.post(
            f"{self.base}/rest/api/3/workflows/create",
            auth=self.auth, headers=self.headers,
            json={
                "scope": {"type": "GLOBAL"},
                "statuses": top_statuses,
                "workflows": [{
                    "name": "PO Workflow — Flexicar",
                    "description": "Flujo 10 estados Product Owner — Flexicar",
                    "startPointLayout": {"x": -100.0, "y": -153.0},
                    "statuses": statuses_list,
                    "transitions": transitions,
                }]
            },
            timeout=30
        )
        self._raise(resp)
        return "PO Workflow — Flexicar"

    def assign_workflow_to_project(self, scheme_id: int, workflow_name: str,
                                   old_status_ids: list[str], new_status_ids: dict[str, str]) -> str:
        """Update workflow scheme draft and publish it. Returns task ID."""
        # Update draft (creates one if it doesn't exist)
        requests.put(
            f"{self.base}/rest/api/2/workflowscheme/{scheme_id}/draft",
            auth=self.auth, headers=self.headers,
            json={"defaultWorkflow": workflow_name, "issueTypeMappings": {}},
            timeout=30
        )
        # Build status migration mappings
        migration = []
        default_new = list(new_status_ids.values())
        for issue_type in ["10001", "10002"]:
            for old_sid in old_status_ids:
                migration.append({
                    "issueTypeId": issue_type,
                    "statusId": old_sid,
                    "newStatusId": default_new[0],
                })
        resp = requests.post(
            f"{self.base}/rest/api/2/workflowscheme/{scheme_id}/draft/publish",
            auth=self.auth, headers=self.headers,
            json={"statusMappings": migration},
            timeout=60
        )
        self._raise(resp)
        return resp.json().get("id", "")

    def wait_for_task(self, task_id: str, max_seconds: int = 30) -> bool:
        """Poll a Jira async task until COMPLETE. Returns True on success."""
        import time
        for _ in range(max_seconds // 2):
            resp = requests.get(
                f"{self.base}/rest/api/2/task/{task_id}",
                auth=self.auth, headers=self.headers, timeout=15
            )
            if resp.ok:
                status = resp.json().get("status", "")
                if status == "COMPLETE":
                    return True
                if status in ("FAILED", "CANCELLED"):
                    return False
            time.sleep(2)
        return False


# ── ADF helpers ──────────────────────────────────────────────────────────────

def _is_table_separator(row: str) -> bool:
    cells = [c.strip() for c in row.split("|") if c.strip()]
    return bool(cells) and all(re.match(r"^:?-+:?$", c) for c in cells)


def _parse_table_row(row: str) -> list[str]:
    cells = row.split("|")
    if cells and not cells[0].strip():
        cells = cells[1:]
    if cells and not cells[-1].strip():
        cells = cells[:-1]
    return [c.strip() for c in cells]


def _make_adf_table(table_lines: list[str]) -> dict:
    rows: list[dict] = []
    header_done = False
    for row in table_lines:
        if _is_table_separator(row):
            header_done = True
            continue
        cells = _parse_table_row(row)
        cell_type = "tableCell" if header_done else "tableHeader"
        rows.append({
            "type": "tableRow",
            "content": [
                {
                    "type": cell_type,
                    "attrs": {},
                    "content": [{"type": "paragraph", "content": _inline(cell)}],
                }
                for cell in cells
            ],
        })
    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": rows,
    }


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

        # Markdown table — collect all consecutive | lines
        elif line.startswith("|"):
            flush_bullets()
            table_lines: list[str] = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            content.append(_make_adf_table(table_lines))
            continue  # i already advanced past the table

        # Headings — check longest prefix first to avoid partial matches
        elif line.startswith("##### "):
            flush_bullets()
            content.append({
                "type": "heading", "attrs": {"level": 5},
                "content": [{"type": "text", "text": line[6:].strip()}],
            })
        elif line.startswith("#### "):
            flush_bullets()
            content.append({
                "type": "heading", "attrs": {"level": 4},
                "content": [{"type": "text", "text": line[5:].strip()}],
            })
        elif line.startswith("### "):
            flush_bullets()
            content.append({
                "type": "heading", "attrs": {"level": 3},
                "content": [{"type": "text", "text": line[4:].strip()}],
            })
        elif line.startswith("## "):
            flush_bullets()
            content.append({
                "type": "heading", "attrs": {"level": 2},
                "content": [{"type": "text", "text": line[3:].strip()}],
            })
        elif line.startswith("# "):
            flush_bullets()
            content.append({
                "type": "heading", "attrs": {"level": 1},
                "content": [{"type": "text", "text": line[2:].strip()}],
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
