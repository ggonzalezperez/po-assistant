from po_assistant.jira_client import md_to_adf


def _nodes(text: str) -> list[dict]:
    return md_to_adf(text)["content"]


def test_h2_heading():
    nodes = _nodes("## Mi sección")
    assert nodes[0]["type"] == "heading"
    assert nodes[0]["attrs"]["level"] == 2
    assert nodes[0]["content"][0]["text"] == "Mi sección"


def test_h3_heading():
    nodes = _nodes("### Subsección")
    assert nodes[0]["attrs"]["level"] == 3


def test_h4_heading():
    nodes = _nodes("#### 1. Petición original")
    assert nodes[0]["type"] == "heading"
    assert nodes[0]["attrs"]["level"] == 4
    assert nodes[0]["content"][0]["text"] == "1. Petición original"


def test_h5_heading():
    nodes = _nodes("##### Detalle")
    assert nodes[0]["attrs"]["level"] == 5


def test_table_basic():
    md = "| Col A | Col B |\n|---|---|\n| Dato 1 | Dato 2 |"
    nodes = _nodes(md)
    assert len(nodes) == 1
    table = nodes[0]
    assert table["type"] == "table"
    rows = table["content"]
    # header row + 1 data row (separator skipped)
    assert len(rows) == 2
    assert rows[0]["content"][0]["type"] == "tableHeader"
    assert rows[1]["content"][0]["type"] == "tableCell"


def test_table_header_text():
    md = "| # | Pregunta | A quién |\n|---|---|---|\n| P-01 | ¿Roles? | María |"
    nodes = _nodes(md)
    table = nodes[0]
    header_cells = table["content"][0]["content"]
    assert header_cells[0]["content"][0]["content"][0]["text"] == "#"
    assert header_cells[1]["content"][0]["content"][0]["text"] == "Pregunta"


def test_table_cell_text():
    md = "| Col |\n|---|\n| valor |"
    nodes = _nodes(md)
    data_cell = nodes[0]["content"][1]["content"][0]
    assert data_cell["type"] == "tableCell"
    assert data_cell["content"][0]["content"][0]["text"] == "valor"


def test_table_followed_by_paragraph():
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n\nPárrafo posterior."
    nodes = _nodes(md)
    assert nodes[0]["type"] == "table"
    assert nodes[1]["type"] == "paragraph"
