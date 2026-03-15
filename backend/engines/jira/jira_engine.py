"""
Jira integration using python-jira.

Reads epics and stories from a Jira project to feed the OrgForge pipeline.
All write-back to Jira (status transitions, comments) also lives here.
"""
from dataclasses import dataclass
from jira import JIRA
from backend.core.config import get_settings

settings = get_settings()


@dataclass
class JiraStory:
    key: str
    summary: str
    description: str | None
    acceptance_criteria: str | None
    status: str
    epic_key: str | None
    story_points: float | None
    assignee: str | None
    labels: list[str]


def get_jira_client(server_url: str, access_token: str) -> JIRA:
    """
    Return an authenticated JIRA client using OAuth2 token (cloud) or PAT.

    For Jira Cloud with OAuth2, pass the access_token as a bearer token.
    For Server/Data Center, use PAT via token_auth.
    """
    return JIRA(
        server=server_url,
        token_auth=access_token,
    )


def get_story(jira: JIRA, issue_key: str) -> JiraStory:
    """Fetch a single Jira issue and return a JiraStory."""
    issue = jira.issue(issue_key)
    fields = issue.fields
    return _to_story(issue.key, fields)


def get_backlog_stories(jira: JIRA, project_key: str, max_results: int = 50) -> list[JiraStory]:
    """
    Return all stories in the project that are in Backlog or To Do status.
    Only retrieves Story issue types.
    """
    jql = (
        f'project = "{project_key}" '
        f'AND issuetype = Story '
        f'AND statusCategory = "To Do" '
        f'ORDER BY created DESC'
    )
    issues = jira.search_issues(jql, maxResults=max_results)
    return [_to_story(i.key, i.fields) for i in issues]


def get_epic_stories(jira: JIRA, epic_key: str) -> list[JiraStory]:
    """Return all stories belonging to a given epic."""
    jql = f'"Epic Link" = {epic_key} OR "Parent" = {epic_key} ORDER BY created DESC'
    issues = jira.search_issues(jql, maxResults=100)
    return [_to_story(i.key, i.fields) for i in issues]


def transition_story(jira: JIRA, issue_key: str, transition_name: str) -> None:
    """Move a Jira story to a new status by transition name (e.g. 'In Progress')."""
    transitions = jira.transitions(issue_key)
    target = next(
        (t for t in transitions if t["name"].lower() == transition_name.lower()), None
    )
    if not target:
        available = [t["name"] for t in transitions]
        raise ValueError(
            f"Transition '{transition_name}' not found. Available: {available}"
        )
    jira.transition_issue(issue_key, target["id"])


def add_comment(jira: JIRA, issue_key: str, body: str) -> None:
    """Add a comment to a Jira issue."""
    jira.add_comment(issue_key, body)


def _to_story(key: str, fields) -> JiraStory:
    """Convert a Jira issue fields object to a JiraStory dataclass."""
    description = _extract_text(getattr(fields, "description", None))

    # Acceptance criteria is often in a custom field — try common names
    ac_field = (
        getattr(fields, "customfield_10016", None)  # typical AC field
        or getattr(fields, "customfield_10014", None)
    )
    acceptance_criteria = _extract_text(ac_field)

    epic_link = (
        getattr(fields, "customfield_10014", None)  # Epic Link
        or getattr(fields, "parent", None)
    )
    epic_key = None
    if hasattr(epic_link, "key"):
        epic_key = epic_link.key
    elif isinstance(epic_link, str):
        epic_key = epic_link

    story_points = getattr(fields, "story_points", None) or getattr(
        fields, "customfield_10016", None
    )
    if isinstance(story_points, str):
        try:
            story_points = float(story_points)
        except ValueError:
            story_points = None

    labels = getattr(fields, "labels", []) or []

    return JiraStory(
        key=key,
        summary=fields.summary,
        description=description,
        acceptance_criteria=acceptance_criteria,
        status=fields.status.name,
        epic_key=epic_key,
        story_points=story_points if isinstance(story_points, (int, float)) else None,
        assignee=fields.assignee.displayName if fields.assignee else None,
        labels=labels,
    )


def _extract_text(value) -> str | None:
    """Best-effort text extraction from Jira field values (plain str or Atlassian doc format)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    # Atlassian Document Format (ADF) — extract plain text from content nodes
    if isinstance(value, dict) and "content" in value:
        return _adf_to_text(value)
    return str(value)


def _adf_to_text(adf: dict) -> str:
    """Recursively extract plain text from an ADF document."""
    parts: list[str] = []
    for node in adf.get("content", []):
        if node.get("type") == "text":
            parts.append(node.get("text", ""))
        elif "content" in node:
            parts.append(_adf_to_text(node))
    return "\n".join(parts).strip()
