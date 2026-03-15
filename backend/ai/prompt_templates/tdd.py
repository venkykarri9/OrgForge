"""Prompt template for TDD document + Mermaid ERD generation."""


def build_tdd_prompt(
    jira_key: str,
    summary: str,
    description: str | None,
    acceptance_criteria: str | None,
    metadata_summary: str,
) -> str:
    ac_block = (
        f"\n\n**Acceptance Criteria:**\n{acceptance_criteria}"
        if acceptance_criteria
        else ""
    )
    desc_block = (
        f"\n\n**Description:**\n{description}"
        if description
        else ""
    )

    return f"""You are a Salesforce technical architect. Given the Jira story and org metadata below, produce:

1. A **Technical Design Document (TDD)** covering:
   - Overview & objectives
   - Salesforce objects/fields involved (new or modified)
   - Apex classes / triggers required
   - Flows or validation rules required
   - Security / profile / permission set changes
   - Test class strategy
   - Deployment notes

2. A **Mermaid ERD** (entity-relationship diagram) showing the objects and their relationships relevant to this story.

---

## Story: {jira_key} — {summary}
{desc_block}{ac_block}

---

## Available Org Metadata (summary)
{metadata_summary}

---

Respond with EXACTLY this structure — no extra commentary:

<TDD>
[Your technical design document in Markdown]
</TDD>

<ERD>
[Your Mermaid erDiagram block — just the diagram, no fences]
</ERD>
"""
