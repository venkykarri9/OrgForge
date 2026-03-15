"""
Claude AI — TDD document + Mermaid ERD generator.

Called at most once per story. Takes story details + metadata catalogue context
and returns a structured TDD and ERD.
"""
import re
import anthropic
from backend.core.config import get_settings
from backend.ai.prompt_templates.tdd import build_tdd_prompt

settings = get_settings()

MAX_METADATA_COMPONENTS = 200  # cap context size sent to Claude


def _summarise_catalogue(catalogue: dict | None) -> str:
    """Convert the full metadata catalogue into a compact text summary for the prompt."""
    if not catalogue:
        return "No metadata catalogue available."

    lines: list[str] = []
    for md_type, items in catalogue.items():
        if not items or (len(items) == 1 and "error" in items[0]):
            continue
        names = [i.get("fullName", "?") for i in items[:MAX_METADATA_COMPONENTS]]
        lines.append(f"**{md_type}** ({len(items)} total): {', '.join(names[:20])}")
        if len(items) > 20:
            lines.append(f"  ... and {len(items) - 20} more")

    return "\n".join(lines) if lines else "Metadata catalogue is empty."


def _parse_response(text: str) -> dict[str, str | None]:
    """Extract <TDD> and <ERD> blocks from Claude's response."""
    tdd_match = re.search(r"<TDD>(.*?)</TDD>", text, re.DOTALL)
    erd_match = re.search(r"<ERD>(.*?)</ERD>", text, re.DOTALL)
    return {
        "tdd": tdd_match.group(1).strip() if tdd_match else text.strip(),
        "erd": erd_match.group(1).strip() if erd_match else None,
    }


async def generate(story, metadata_catalogue: dict | None) -> dict[str, str | None]:
    """
    Generate a TDD document and Mermaid ERD for the given story.

    Args:
        story: Story ORM instance
        metadata_catalogue: dict from metadata_puller (may be None)

    Returns:
        {"tdd": "<markdown>", "erd": "<mermaid erDiagram>"}
    """
    metadata_summary = _summarise_catalogue(metadata_catalogue)

    prompt = build_tdd_prompt(
        jira_key=story.jira_issue_key,
        summary=story.jira_summary,
        description=story.jira_description,
        acceptance_criteria=story.jira_acceptance_criteria,
        metadata_summary=metadata_summary,
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    return _parse_response(response_text)
