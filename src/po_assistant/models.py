from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class POEstado(str, Enum):
    INTAKE = "po-intake"
    TRIAGE = "po-triage"
    DISCOVERY = "po-discovery"
    DEFINICION = "po-definicion"
    SIGN_OFF_SH = "po-signoff-sh"
    DOR_GATE = "po-dor-gate"
    HANDSHAKE = "po-handshake"
    EN_DESARROLLO = "po-en-desarrollo"
    UAT = "po-uat"
    RELEASE = "po-release"
    CERRADO = "po-cerrado"
    RECHAZADO = "po-rechazado"
    APLAZADO = "po-aplazado"

    @property
    def display(self) -> str:
        mapping = {
            "po-intake": "INTAKE",
            "po-triage": "TRIAGE",
            "po-discovery": "DISCOVERY",
            "po-definicion": "DEFINICIÓN",
            "po-signoff-sh": "SIGN-OFF SH",
            "po-dor-gate": "DOR GATE",
            "po-handshake": "HANDSHAKE",
            "po-en-desarrollo": "EN DESARROLLO",
            "po-uat": "UAT",
            "po-release": "RELEASE",
            "po-cerrado": "CERRADO",
            "po-rechazado": "RECHAZADO",
            "po-aplazado": "APLAZADO",
        }
        return mapping.get(self.value, self.value.upper())

    @classmethod
    def from_labels(cls, labels: list[str]) -> Optional["POEstado"]:
        for label in labels:
            for estado in cls:
                if estado.value == label:
                    return estado
        return None


class TipoPeticion(str, Enum):
    PROBLEMA = "problema"
    IDEA = "idea"
    URGENCIA = "urgencia"
    MEJORA = "mejora"
    INCIDENCIA = "incidencia"


@dataclass
class IntakeResult:
    titulo: str
    tipo_peticion: TipoPeticion
    descripcion: str
    prioridad_sugerida: str
    razon_prioridad: str
    alerta_urgencia: bool
    dudas_para_el_po: list[str]


@dataclass
class DorBlockResult:
    numero: int
    nombre: str
    cumple: bool
    critico: bool
    gap: Optional[str] = None
    accion: Optional[str] = None


# Bloques críticos que siempre deben cumplir (aunque score ≥ 11)
DOR_CRITICAL_BLOCKS = {1, 5, 7, 9, 10, 12}

DOR_BLOCK_NAMES = {
    1: "Problema (no solución)",
    2: "Usuario beneficiado",
    3: "Stakeholder solicitante + Validador",
    4: "Contexto actual revisado",
    5: "Alcance + Exclusiones explícitas",
    6: "MVP identificado",
    7: "Reglas de negocio críticas",
    8: "Datos / Campos / Estados / Integraciones",
    9: "Casuística (happy + límites + errores)",
    10: "Criterios de aceptación verificables",
    11: "Prioridad justificada por valor/riesgo",
    12: "Validador UAT designado",
}


@dataclass
class DorGateResult:
    score: int
    bloques: list[DorBlockResult]
    pasa: bool
    critico_fallido: bool
    bloques_fallidos: list[int]

    def comentario_jira(self) -> str:
        lines = [f"## DoR Gate — {self.score}/12\n"]
        for b in self.bloques:
            icon = "✅" if b.cumple else ("❌ CRÍTICO" if b.critico else "⚠️")
            lines.append(f"**Bloque {b.numero:02d} — {b.nombre}** {icon}")
            if not b.cumple and b.gap:
                lines.append(f"  → Gap: {b.gap}")
            if not b.cumple and b.accion:
                lines.append(f"  → Acción: {b.accion}")
        lines.append("")
        if self.pasa:
            lines.append(f"**RESULTADO: DOR GATE OK ✅ ({self.score}/12). Pasa a HANDSHAKE.**")
        else:
            lines.append(f"**RESULTADO: DOR GATE KO ❌ ({self.score}/12).**")
            lines.append(f"Bloques fallidos: {', '.join(str(n) for n in self.bloques_fallidos)}")
            lines.append("Sin reproche. Esta HU vuelve a DEFINICIÓN cuando esté lista.")
        return "\n".join(lines)


@dataclass
class JiraIssue:
    key: str
    summary: str
    description: str
    status: str
    labels: list[str]
    assignee: Optional[str]
    created: str
    updated: str
    reporter: Optional[str] = None
    custom_fields: dict = field(default_factory=dict)

    @property
    def po_estado(self) -> Optional[POEstado]:
        return POEstado.from_labels(self.labels)


@dataclass
class UrgenciaResult:
    titulo: str
    descripcion: str
    prioridad_sugerida: str
    razon_prioridad: str
    impacto: str
    causa_probable: str
    accion_correctiva: str
    rollback: str
    checks_verificacion: list[str]
