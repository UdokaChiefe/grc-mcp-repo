"""
Read-only GitHub evidence collector.

Checks branch protection and CODEOWNERS presence via the GitHub REST API,
using a token scoped to Administration:read and Contents:read only.
Never writes to, modifies, or configures the audited repository.

IMPORTANT: GitHub returns 404 both when a setting is genuinely absent AND
when the repo/branch can't be found or the token lacks access to confirm.
This module preserves that ambiguity rather than collapsing it into a
false "control is missing" conclusion — see each function's "note" field.
"""

import os
from typing import Any

import requests

GITHUB_API = "https://api.github.com"

CONTROL_MAP = {
    "branch_protection": ["SOC2-CC8.1", "ISO27001-A.8.32"],
    "codeowners": ["SOC2-CC8.1", "ISO27001-A.5.3"],
}


def _headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Create a .env file in this project "
            "with GITHUB_TOKEN=your_token_value_here (see .env.example)."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def check_branch_protection(owner: str, repo: str, branch: str) -> dict[str, Any]:
    """Check active protection rules for a branch. Read-only — never modifies
    the repo.

    Uses GitHub's newer "rules for a branch" endpoint
    (/repos/{owner}/{repo}/rules/branches/{branch}) rather than the classic
    /branches/{branch}/protection endpoint. The classic endpoint only sees
    "classic" branch protection and returns a 404 "Branch not protected"
    even when the branch IS protected via a Ruleset — a documented GitHub
    quirk (rulesets and classic protection are separate backend systems).
    The rules endpoint correctly reflects protection from either source,
    and works whether or not the branch has been created yet.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/rules/branches/{branch}"
    resp = requests.get(url, headers=_headers(), timeout=15)

    if resp.status_code == 200:
        rules = resp.json()
        if rules:
            return {
                "present": True,
                "status": "confirmed_present",
                "http_status": 200,
                "rule_types": sorted({r.get("type") for r in rules if isinstance(r, dict)}),
                "details": rules,
            }
        return {
            "present": False,
            "status": "confirmed_absent",
            "http_status": 200,
            "note": (
                "GitHub returned an empty rule list — no active classic "
                "protection or ruleset applies to this branch. This is a "
                "confirmed result, not an ambiguous one, since the endpoint "
                "responded successfully."
            ),
        }
    if resp.status_code == 401:
        return {"present": None, "status": "unauthorized", "http_status": 401,
                 "note": "Token invalid or expired."}
    if resp.status_code == 403:
        return {"present": None, "status": "forbidden", "http_status": 403,
                 "note": "Token lacks required read access for this repository."}
    if resp.status_code == 404:
        return {
            "present": None,
            "status": "not_found_or_unconfirmed",
            "http_status": 404,
            "note": (
                "404 here usually means the repository itself wasn't found — "
                "check the owner/repo spelling and that the token has access "
                "to it. (The branch does not need to exist for this endpoint "
                "to succeed, so a 404 is not about the branch name.)"
            ),
        }
    return {"present": None, "status": "error", "http_status": resp.status_code,
             "details": resp.text}


def check_codeowners(owner: str, repo: str, branch: str) -> dict[str, Any]:
    """Check common CODEOWNERS locations. Read-only."""
    candidates = ["CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"]
    for path in candidates:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        resp = requests.get(url, headers=_headers(), params={"ref": branch}, timeout=15)
        if resp.status_code == 200:
            return {
                "present": True,
                "status": "confirmed_present",
                "http_status": 200,
                "path": path,
            }
        if resp.status_code == 401:
            return {"present": None, "status": "unauthorized", "http_status": 401}
        if resp.status_code == 403:
            return {"present": None, "status": "forbidden", "http_status": 403}
        # 404 -> try the next candidate path

    return {
        "present": False,
        "status": "not_found_or_unconfirmed",
        "http_status": 404,
        "note": (
            "No CODEOWNERS file found at common paths. Absence at these paths "
            "doesn't fully rule out an unusual location — human review recommended."
        ),
    }


def collect_github_evidence(owner: str, repo: str, branch: str) -> dict[str, Any]:
    bp = check_branch_protection(owner, repo, branch)
    co = check_codeowners(owner, repo, branch)
    return {
        "source": "github",
        "repository": f"{owner}/{repo}",
        "branch": branch,
        "checks": {
            "branch_protection": {**bp, "control_refs": CONTROL_MAP["branch_protection"]},
            "codeowners": {**co, "control_refs": CONTROL_MAP["codeowners"]},
        },
    }
