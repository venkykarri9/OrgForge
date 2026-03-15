"""
Claude AI — Apex code review against TDD.

Called at most once per story, after the developer has written their Apex.
"""
import anthropic
from backend.core.config import get_settings
from backend.ai.prompt_templates.code_review import build_code_review_prompt

settings = get_settings()


async def review(
    story,
    apex_files: dict[str, str],
) -> str:
    """
    Review Apex code against the story's TDD document.

    Args:
        story: Story ORM instance (must have tdd_document set)
        apex_files: dict of {class_name: apex_source_body}

    Returns:
        Markdown code review string
    """
    if not story.tdd_document:
        raise ValueError("Story has no TDD document — generate it first")
    if not apex_files:
        raise ValueError("No Apex files provided for review")

    prompt = build_code_review_prompt(
        jira_key=story.jira_issue_key,
        tdd_document=story.tdd_document,
        apex_files=apex_files,
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.claude_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
