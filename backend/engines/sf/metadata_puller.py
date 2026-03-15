"""
Pull Salesforce metadata using the Metadata API and Tooling API via simple_salesforce.

Pulled metadata is stored in S3 for later use by the package builder and Claude AI context.
"""
import json
import boto3
from simple_salesforce import Salesforce
from backend.core.config import get_settings

settings = get_settings()

s3 = boto3.client("s3", region_name=settings.aws_region)

# Full set of Salesforce metadata types to pull for the org catalogue.
# Covers all major categories: code, UI, automation, data model, security, analytics.
DEFAULT_METADATA_TYPES = [
    # ── Data Model ─────────────────────────────────────────────────────────
    "CustomObject",
    "CustomField",
    "CustomMetadata",
    "CustomSetting",
    "RecordType",
    "BusinessProcess",
    "CompactLayout",
    "FieldSet",
    "Index",
    "SharingReason",
    "ListView",
    # ── Apex / Code ────────────────────────────────────────────────────────
    "ApexClass",
    "ApexTrigger",
    "ApexPage",
    "ApexComponent",
    # ── Lightning / UI ─────────────────────────────────────────────────────
    "LightningComponentBundle",
    "AuraDefinitionBundle",
    "FlexiPage",
    "Layout",
    "CustomTab",
    "AppMenu",
    "CustomApplication",
    "HomePageLayout",
    "CustomPageWebLink",
    # ── Automation ─────────────────────────────────────────────────────────
    "Flow",
    "FlowDefinition",
    "WorkflowRule",
    "WorkflowFieldUpdate",
    "WorkflowAlert",
    "WorkflowTask",
    "WorkflowOutboundMessage",
    "ProcessBuilder",
    "ValidationRule",
    "DuplicateRule",
    "MatchingRule",
    "AssignmentRule",
    "AutoResponseRule",
    "EscalationRule",
    # ── Security / Access ──────────────────────────────────────────────────
    "Profile",
    "PermissionSet",
    "PermissionSetGroup",
    "Role",
    "Group",
    "SharingSet",
    "SharingCriteriaRule",
    "SharingOwnerRule",
    "MutingPermissionSet",
    # ── Integration ────────────────────────────────────────────────────────
    "ConnectedApp",
    "NamedCredential",
    "ExternalDataSource",
    "RemoteSiteSetting",
    "CorsWhitelistOrigin",
    "CustomPermission",
    # ── Analytics / CRM ────────────────────────────────────────────────────
    "Report",
    "ReportType",
    "Dashboard",
    "AnalyticSnapshot",
    # ── Email & Templates ──────────────────────────────────────────────────
    "EmailTemplate",
    "LetterHead",
    # ── Static Resources & Content ─────────────────────────────────────────
    "StaticResource",
    "Document",
    "ContentAsset",
    # ── Labels & Settings ──────────────────────────────────────────────────
    "CustomLabel",
    "CustomSite",
    "Network",
    "SiteDotCom",
    "Settings",
    "OrgPreferenceSettings",
    # ── Territory / Forecasting ────────────────────────────────────────────
    "Territory2",
    "Territory2Model",
    "Territory2Rule",
    "Territory2Type",
    # ── Chatter / Communities ──────────────────────────────────────────────
    "ChatterExtension",
    "PathAssistant",
    "GlobalPicklist",
    "GlobalValueSet",
]


def list_metadata(sf: Salesforce, metadata_type: str) -> list[dict]:
    """
    List all members of a given metadata type using the Metadata API (listMetadata).
    Returns a list of dicts with name, lastModifiedDate, etc.
    """
    result = sf.mdapi.list(
        [{"type": metadata_type}],
        "60.0",
    )
    if not result:
        return []
    if isinstance(result, dict):
        result = [result]
    return [
        {
            "type": metadata_type,
            "fullName": item.get("fullName"),
            "lastModifiedDate": item.get("lastModifiedDate"),
            "lastModifiedByName": item.get("lastModifiedByName"),
            "fileName": item.get("fileName"),
        }
        for item in result
    ]


def pull_all_metadata(sf: Salesforce, org_id: str) -> dict[str, list[dict]]:
    """
    Pull the metadata catalogue for all DEFAULT_METADATA_TYPES.
    Returns a dict keyed by metadata type.
    Stores the result in S3 under orgs/{org_id}/metadata_catalogue.json.
    Also saves a computed metrics snapshot to S3.
    """
    catalogue: dict[str, list[dict]] = {}
    for md_type in DEFAULT_METADATA_TYPES:
        try:
            catalogue[md_type] = list_metadata(sf, md_type)
        except Exception as exc:
            catalogue[md_type] = [{"error": str(exc)}]

    _save_catalogue_to_s3(org_id, catalogue)
    _save_metrics_to_s3(org_id, compute_metrics(catalogue))
    return catalogue


def compute_metrics(catalogue: dict[str, list[dict]]) -> dict:
    """
    Derive display-ready metrics from a metadata catalogue.
    Returns grouped sections + per-type counts + grand total.
    """
    # Groups: each entry is (metadata_type, display_label)
    GROUPS: dict[str, list[tuple[str, str]]] = {
        "Data Model": [
            ("CustomObject", "Custom Objects"),
            ("CustomField", "Custom Fields"),
            ("CustomMetadata", "Custom Metadata Types"),
            ("CustomSetting", "Custom Settings"),
            ("RecordType", "Record Types"),
            ("BusinessProcess", "Business Processes"),
            ("CompactLayout", "Compact Layouts"),
            ("FieldSet", "Field Sets"),
            ("Index", "Indexes"),
            ("SharingReason", "Sharing Reasons"),
            ("ListView", "List Views"),
            ("GlobalPicklist", "Global Picklists"),
            ("GlobalValueSet", "Global Value Sets"),
        ],
        "Apex & Code": [
            ("ApexClass", "Apex Classes"),
            ("ApexTrigger", "Apex Triggers"),
            ("ApexPage", "Visualforce Pages"),
            ("ApexComponent", "Visualforce Components"),
        ],
        "Lightning & UI": [
            ("LightningComponentBundle", "LWC Components"),
            ("AuraDefinitionBundle", "Aura Components"),
            ("FlexiPage", "Lightning Pages"),
            ("Layout", "Page Layouts"),
            ("CustomTab", "Custom Tabs"),
            ("AppMenu", "App Menus"),
            ("CustomApplication", "Custom Applications"),
            ("HomePageLayout", "Home Page Layouts"),
            ("CustomPageWebLink", "Web Links"),
        ],
        "Automation": [
            ("Flow", "Flows"),
            ("FlowDefinition", "Flow Definitions"),
            ("WorkflowRule", "Workflow Rules"),
            ("WorkflowFieldUpdate", "Field Updates"),
            ("WorkflowAlert", "Email Alerts"),
            ("WorkflowTask", "Workflow Tasks"),
            ("WorkflowOutboundMessage", "Outbound Messages"),
            ("ValidationRule", "Validation Rules"),
            ("DuplicateRule", "Duplicate Rules"),
            ("MatchingRule", "Matching Rules"),
            ("AssignmentRule", "Assignment Rules"),
            ("AutoResponseRule", "Auto-Response Rules"),
            ("EscalationRule", "Escalation Rules"),
        ],
        "Security & Access": [
            ("Profile", "Profiles"),
            ("PermissionSet", "Permission Sets"),
            ("PermissionSetGroup", "Permission Set Groups"),
            ("MutingPermissionSet", "Muting Permission Sets"),
            ("Role", "Roles"),
            ("Group", "Public Groups"),
            ("SharingSet", "Sharing Sets"),
            ("SharingCriteriaRule", "Sharing Criteria Rules"),
            ("SharingOwnerRule", "Sharing Owner Rules"),
            ("CustomPermission", "Custom Permissions"),
        ],
        "Integration": [
            ("ConnectedApp", "Connected Apps"),
            ("NamedCredential", "Named Credentials"),
            ("ExternalDataSource", "External Data Sources"),
            ("RemoteSiteSetting", "Remote Site Settings"),
            ("CorsWhitelistOrigin", "CORS Origins"),
        ],
        "Analytics": [
            ("Report", "Reports"),
            ("ReportType", "Report Types"),
            ("Dashboard", "Dashboards"),
            ("AnalyticSnapshot", "Analytic Snapshots"),
        ],
        "Email & Content": [
            ("EmailTemplate", "Email Templates"),
            ("LetterHead", "Letterheads"),
            ("StaticResource", "Static Resources"),
            ("Document", "Documents"),
            ("ContentAsset", "Content Assets"),
            ("CustomLabel", "Custom Labels"),
        ],
        "Sites & Communities": [
            ("CustomSite", "Custom Sites"),
            ("Network", "Communities / Networks"),
            ("SiteDotCom", "Site.com Sites"),
        ],
        "Territory Management": [
            ("Territory2", "Territories"),
            ("Territory2Model", "Territory Models"),
            ("Territory2Rule", "Territory Rules"),
            ("Territory2Type", "Territory Types"),
        ],
    }

    groups_out: list[dict] = []
    totals: dict[str, int] = {}
    grand_total = 0

    for group_name, type_list in GROUPS.items():
        group_items: list[dict] = []
        group_total = 0

        for md_type, label in type_list:
            items = catalogue.get(md_type, [])
            valid = [i for i in items if "error" not in i]
            count = len(valid)
            group_total += count
            grand_total += count
            totals[md_type] = count

            dates = [i.get("lastModifiedDate") for i in valid if i.get("lastModifiedDate")]
            last_modified = max(dates) if dates else None

            group_items.append({
                "type": md_type,
                "label": label,
                "count": count,
                "last_modified": last_modified,
            })

        groups_out.append({
            "group": group_name,
            "total": group_total,
            "items": group_items,
        })

    # Also include any types in the catalogue that aren't in a group
    ungrouped: list[dict] = []
    grouped_types = {md_type for g in GROUPS.values() for md_type, _ in g}
    for md_type, items in catalogue.items():
        if md_type in grouped_types:
            continue
        valid = [i for i in items if "error" not in i]
        count = len(valid)
        if count == 0:
            continue
        grand_total += count
        totals[md_type] = count
        ungrouped.append({"type": md_type, "label": md_type, "count": count, "last_modified": None})

    if ungrouped:
        groups_out.append({"group": "Other", "total": sum(i["count"] for i in ungrouped), "items": ungrouped})

    # Flat summary (all items, for backwards compatibility)
    summary = [item for g in groups_out for item in g["items"]]

    return {
        "groups": groups_out,
        "summary": summary,
        "totals": totals,
        "grand_total": grand_total,
    }


def _save_metrics_to_s3(org_id: str, metrics: dict) -> None:
    key = f"orgs/{org_id}/metrics.json"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=json.dumps(metrics, default=str),
        ContentType="application/json",
    )


def load_metrics_from_s3(org_id: str) -> dict | None:
    """Load the previously computed metrics snapshot from S3."""
    key = f"orgs/{org_id}/metrics.json"
    try:
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
        return json.loads(obj["Body"].read())
    except Exception:
        return None


def _save_catalogue_to_s3(org_id: str, catalogue: dict) -> None:
    key = f"orgs/{org_id}/metadata_catalogue.json"
    s3.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=json.dumps(catalogue, default=str),
        ContentType="application/json",
    )


def load_catalogue_from_s3(org_id: str) -> dict | None:
    """Load the previously pulled metadata catalogue from S3."""
    key = f"orgs/{org_id}/metadata_catalogue.json"
    try:
        obj = s3.get_object(Bucket=settings.s3_bucket, Key=key)
        return json.loads(obj["Body"].read())
    except s3.exceptions.NoSuchKey:
        return None


def get_apex_class_body(sf: Salesforce, class_name: str) -> str | None:
    """Retrieve the source body of an Apex class via the Tooling API."""
    result = sf.toolingexecute(
        f"SELECT Id, Body FROM ApexClass WHERE Name = '{class_name}' LIMIT 1"
    )
    records = result.get("records", [])
    if records:
        return records[0].get("Body")
    return None


def get_object_fields(sf: Salesforce, object_api_name: str) -> list[dict]:
    """Describe a Salesforce object and return its field definitions."""
    described = sf.__getattr__(object_api_name).describe()
    return [
        {
            "name": f["name"],
            "label": f["label"],
            "type": f["type"],
            "referenceTo": f.get("referenceTo", []),
            "required": not f.get("nillable", True),
        }
        for f in described.get("fields", [])
    ]
