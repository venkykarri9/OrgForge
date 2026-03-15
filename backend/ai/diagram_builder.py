"""
Claude AI — standalone Mermaid ERD generator.

Used when a human requests a fresh object relationship diagram
without a full TDD (e.g. from the metadata browser).
"""
import json
import anthropic
from backend.core.config import get_settings
from backend.ai.prompt_templates.diagram import build_diagram_prompt

settings = get_settings()


async def build_erd(objects: list[dict]) -> str:
    """
    Generate a Mermaid erDiagram from a list of SF object definitions.

    Args:
        objects: list of dicts, each with keys: name, fields (list of field dicts)

    Returns:
        Mermaid erDiagram string (starting with 'erDiagram')
    """
    objects_json = json.dumps(objects, indent=2)
    prompt = build_diagram_prompt(objects_json)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    diagram = message.content[0].text.strip()
    # Ensure it starts correctly
    if not diagram.startswith("erDiagram"):
        diagram = "erDiagram\n" + diagram
    return diagram
