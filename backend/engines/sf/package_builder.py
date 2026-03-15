"""
Build a Salesforce package.xml from a list of changed metadata components.

Pure Python — no LLM involved. Detects changed files from a git diff and
maps them to Salesforce metadata types.
"""
import re
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# Maps SFDX source-format directory/extension to SF metadata type
SFDX_TYPE_MAP: dict[str, str] = {
    "objects": "CustomObject",
    "fields": "CustomField",
    "classes": "ApexClass",
    "triggers": "ApexTrigger",
    "flows": "Flow",
    "validationRules": "ValidationRule",
    "layouts": "Layout",
    "permissionsets": "PermissionSet",
    "profiles": "Profile",
    "tabs": "CustomTab",
    "lwc": "LightningComponentBundle",
    "aura": "AuraDefinitionBundle",
    "pages": "ApexPage",
    "components": "ApexComponent",
    "staticresources": "StaticResource",
    "customMetadata": "CustomMetadata",
    "labels": "CustomLabel",
    "email": "EmailTemplate",
    "reports": "Report",
    "dashboards": "Dashboard",
}

SF_API_VERSION = "60.0"


def detect_changed_components(diff_files: list[str]) -> list[dict[str, str]]:
    """
    Given a list of changed file paths (from git diff), return a list of
    {'type': <MetadataType>, 'member': <fullName>} dicts.

    Handles SFDX source-format paths like:
      force-app/main/default/classes/MyClass.cls
      force-app/main/default/objects/Account/fields/My_Field__c.field-meta.xml
    """
    components: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for path_str in diff_files:
        path = Path(path_str)
        parts = path.parts

        # Find the metadata type directory in the path
        for i, part in enumerate(parts):
            if part in SFDX_TYPE_MAP:
                md_type = SFDX_TYPE_MAP[part]
                member = _extract_member_name(parts, i, md_type)
                if member:
                    key = (md_type, member)
                    if key not in seen:
                        seen.add(key)
                        components.append({"type": md_type, "member": member})
                break

    return components


def _extract_member_name(parts: tuple[str, ...], type_idx: int, md_type: str) -> str | None:
    """Extract the fullName/member name from the path parts after the type directory."""
    if type_idx + 1 >= len(parts):
        return None

    next_part = parts[type_idx + 1]

    # CustomField: objects/Account/fields/My_Field__c.field-meta.xml → Account.My_Field__c
    if md_type == "CustomField" and type_idx >= 2:
        object_name = parts[type_idx - 1]
        field_name = re.sub(r"\.field-meta\.xml$", "", next_part)
        return f"{object_name}.{field_name}"

    # ValidationRule: objects/Account/validationRules/Rule_Name.validationRule-meta.xml
    if md_type == "ValidationRule" and type_idx >= 2:
        object_name = parts[type_idx - 1]
        rule_name = re.sub(r"\.[a-z]+-meta\.xml$", "", next_part)
        return f"{object_name}.{rule_name}"

    # LWC / Aura: lwc/myComponent/... → myComponent
    if md_type in ("LightningComponentBundle", "AuraDefinitionBundle"):
        return next_part  # just the folder name

    # Default: strip -meta.xml and extension
    member = re.sub(r"\.[a-z]+-meta\.xml$", "", next_part)
    member = re.sub(r"\.(cls|trigger|page|component|resource)$", "", member)
    return member if member else None


def build_package_xml(components: list[dict[str, str]], api_version: str = SF_API_VERSION) -> str:
    """
    Build a package.xml string from a list of {'type', 'member'} dicts.

    Returns the XML as a formatted string.
    """
    # Group members by type
    by_type: dict[str, list[str]] = {}
    for comp in components:
        by_type.setdefault(comp["type"], []).append(comp["member"])

    root = Element("Package", xmlns="http://soap.sforce.com/2006/04/metadata")

    for md_type in sorted(by_type):
        types_el = SubElement(root, "types")
        for member in sorted(by_type[md_type]):
            m_el = SubElement(types_el, "members")
            m_el.text = member
        name_el = SubElement(types_el, "name")
        name_el.text = md_type

    version_el = SubElement(root, "version")
    version_el.text = api_version

    raw = tostring(root, encoding="unicode")
    return minidom.parseString(raw).toprettyxml(indent="    ")
