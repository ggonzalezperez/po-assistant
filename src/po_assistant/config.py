from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

load_dotenv()


@dataclass
class JiraFields:
    dor_score: str = ""
    dor_gaps: str = ""
    ia_asistida: str = ""
    tipo_peticion: str = ""
    validador_uat: str = ""
    fecha_signoff: str = ""


@dataclass
class Config:
    jira_base_url: str
    jira_email: str
    jira_api_token: str
    jira_po_project_key: str
    jira_dev_project_key: str
    anthropic_api_key: str
    claude_model: str
    docs_path: Path
    environment: str
    dry_run: bool
    fields: JiraFields = field(default_factory=JiraFields)
    po_team: dict[str, str] = field(default_factory=dict)
    pe_email: str = ""


def load_config() -> Config:
    missing: list[str] = []

    def require(key: str) -> str:
        val = os.getenv(key, "").strip()
        if not val:
            missing.append(key)
        return val

    def optional(key: str, default: str = "") -> str:
        return os.getenv(key, default).strip()

    po_team: dict[str, str] = {}
    raw_team = optional("PO_TEAM")
    if raw_team:
        for entry in raw_team.split(","):
            parts = entry.strip().split(":")
            if len(parts) == 2:
                po_team[parts[0].strip()] = parts[1].strip()

    config = Config(
        jira_base_url=require("JIRA_BASE_URL").rstrip("/"),
        jira_email=require("JIRA_EMAIL"),
        jira_api_token=require("JIRA_API_TOKEN"),
        jira_po_project_key=optional("JIRA_PO_PROJECT_KEY", "FP"),
        jira_dev_project_key=optional("JIRA_DEV_PROJECT_KEY", "FI"),
        anthropic_api_key=require("ANTHROPIC_API_KEY"),
        claude_model=optional("CLAUDE_MODEL", "claude-sonnet-4-6"),
        docs_path=Path(optional("DOCS_PATH", ".")),
        environment=optional("ENVIRONMENT", "development"),
        dry_run=optional("DRY_RUN", "false").lower() == "true",
        fields=JiraFields(
            dor_score=optional("JIRA_FIELD_DOR_SCORE"),
            dor_gaps=optional("JIRA_FIELD_DOR_GAPS"),
            ia_asistida=optional("JIRA_FIELD_IA_ASISTIDA"),
            tipo_peticion=optional("JIRA_FIELD_TIPO_PETICION"),
            validador_uat=optional("JIRA_FIELD_VALIDADOR_UAT"),
            fecha_signoff=optional("JIRA_FIELD_FECHA_SIGNOFF"),
        ),
        po_team=po_team,
        pe_email=optional("PE_EMAIL"),
    )

    if missing:
        print(f"\n[ERROR] Variables de entorno obligatorias no configuradas: {', '.join(missing)}")
        print("Copia .env.example → .env y rellena los valores.\n")
        sys.exit(1)

    return config
