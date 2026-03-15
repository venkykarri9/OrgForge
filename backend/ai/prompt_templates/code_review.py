"""Prompt template for Apex code review against the TDD."""


def build_code_review_prompt(
    jira_key: str,
    tdd_document: str,
    apex_files: dict[str, str],
) -> str:
    files_block = "\n\n".join(
        f"### {name}\n```apex\n{body}\n```"
        for name, body in apex_files.items()
    )

    return f"""You are a Salesforce code quality expert. Review the Apex code below against the Technical Design Document (TDD) for story {jira_key}.

## TDD
{tdd_document}

---

## Apex Code Under Review
{files_block}

---

Produce a structured code review covering:
1. **TDD Compliance** — does the code implement everything specified?
2. **Best Practices** — bulkification, trigger frameworks, selector/service layers
3. **Security** — CRUD/FLS checks, sharing rules, SOQL injection risks
4. **Test Coverage** — are all branches covered? positive + negative cases?
5. **Issues** — list each issue with severity (CRITICAL / MAJOR / MINOR) and suggested fix

Respond in Markdown. Be concise and actionable.
"""
