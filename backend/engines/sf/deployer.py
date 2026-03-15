"""
Salesforce validate and deploy using the SF CLI (subprocess).

Runs: sf project deploy [validate|start] --manifest package.xml
Captures output and async job ID for status polling.
"""
import subprocess
import tempfile
import json
import re
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DeployResult:
    success: bool
    job_id: str | None
    stdout: str
    stderr: str
    error_message: str | None = None


def _run_sf_cli(args: list[str], cwd: str | None = None) -> tuple[str, str, int]:
    """Run an SF CLI command and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        ["sf"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.stdout, result.stderr, result.returncode


def validate(
    org_alias: str,
    package_xml_content: str,
    project_dir: str,
    test_level: str = "RunLocalTests",
) -> DeployResult:
    """
    Run a validate-only deploy (check-only) using SF CLI.

    Args:
        org_alias: SF CLI org alias (set up via `sf org login`)
        package_xml_content: XML string of the package.xml
        project_dir: path to the local SFDX project root
        test_level: RunLocalTests | RunAllTestsInOrg | NoTestRun

    Returns DeployResult with success flag, job ID, and output.
    """
    with tempfile.NamedTemporaryFile(
        suffix=".xml", mode="w", delete=False, dir=project_dir
    ) as tmp:
        tmp.write(package_xml_content)
        package_path = tmp.name

    try:
        stdout, stderr, rc = _run_sf_cli(
            [
                "project", "deploy", "validate",
                "--manifest", package_path,
                "--target-org", org_alias,
                "--test-level", test_level,
                "--json",
            ],
            cwd=project_dir,
        )
        return _parse_deploy_output(stdout, stderr, rc)
    finally:
        Path(package_path).unlink(missing_ok=True)


def deploy(
    org_alias: str,
    package_xml_content: str,
    project_dir: str,
    test_level: str = "RunLocalTests",
) -> DeployResult:
    """
    Deploy to Salesforce using SF CLI.

    Args:
        org_alias: SF CLI org alias
        package_xml_content: XML string of the package.xml
        project_dir: path to the local SFDX project root
        test_level: RunLocalTests | RunAllTestsInOrg | NoTestRun

    Returns DeployResult with success flag, job ID, and output.
    """
    with tempfile.NamedTemporaryFile(
        suffix=".xml", mode="w", delete=False, dir=project_dir
    ) as tmp:
        tmp.write(package_xml_content)
        package_path = tmp.name

    try:
        stdout, stderr, rc = _run_sf_cli(
            [
                "project", "deploy", "start",
                "--manifest", package_path,
                "--target-org", org_alias,
                "--test-level", test_level,
                "--json",
            ],
            cwd=project_dir,
        )
        return _parse_deploy_output(stdout, stderr, rc)
    finally:
        Path(package_path).unlink(missing_ok=True)


def poll_status(job_id: str, org_alias: str) -> DeployResult:
    """Poll the status of an async deploy job."""
    stdout, stderr, rc = _run_sf_cli(
        [
            "project", "deploy", "report",
            "--job-id", job_id,
            "--target-org", org_alias,
            "--json",
        ]
    )
    return _parse_deploy_output(stdout, stderr, rc)


def _parse_deploy_output(stdout: str, stderr: str, returncode: int) -> DeployResult:
    """Parse SF CLI --json output into a DeployResult."""
    job_id: str | None = None
    error_msg: str | None = None

    try:
        data = json.loads(stdout)
        result_data = data.get("result", data)
        job_id = result_data.get("id") or result_data.get("jobId")
        success = returncode == 0 and data.get("status", 1) == 0
        if not success:
            error_msg = data.get("message") or stderr
    except (json.JSONDecodeError, KeyError):
        success = returncode == 0
        # Try to extract job ID from stdout with a regex fallback
        match = re.search(r"[0-9A-Za-z]{15,18}", stdout)
        if match:
            job_id = match.group(0)
        error_msg = stderr if not success else None

    return DeployResult(
        success=success,
        job_id=job_id,
        stdout=stdout,
        stderr=stderr,
        error_message=error_msg,
    )
