"""Prompt template for standalone object relationship diagram generation."""


def build_diagram_prompt(objects_json: str) -> str:
    return f"""You are a Salesforce data architect. Given the object and field definitions below, generate a Mermaid erDiagram showing all objects, their key fields, and relationships (lookups, master-detail).

## Object Definitions (JSON)
{objects_json}

---

Respond with ONLY the Mermaid erDiagram block — no explanation, no code fences, just the diagram starting with `erDiagram`.
"""
