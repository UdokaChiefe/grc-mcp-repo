"""
grc-evidence-mcp

Read-only compliance evidence collection MCP server.
Reads evidence FROM audited systems, writes evidence TO a local landing
zone (SQLite). Never modifies the audited system itself.
"""

from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .store import StateStore
from .github import collect_github_evidence

load_dotenv()  # loads GITHUB_TOKEN (and anything else) from .env, if present

store = StateStore()

mcp = FastMCP("grc-evidence-mcp")

# Registry of evidence sources. Each entry flags whether it's a working
# source or a stub placeholder ("stub": True).
EVIDENCE_SOURCES: list[dict[str, Any]] = [
    {
        "id": "github",
        "name": "GitHub",
        "description": "Branch protection and CODEOWNERS checks via the GitHub REST API.",
        "stub": False,
    },
    {
        "id": "stub_source_1",
        "name": "Example Stub Source",
        "description": "Placeholder source — not implemented yet.",
        "stub": True,
    },
]


@mcp.tool()
def list_evidence_sources() -> list[dict[str, Any]]:
    """List available evidence sources for compliance collection.
    Each entry flags whether it's a working source or a stub placeholder."""
    return EVIDENCE_SOURCES


@mcp.tool()
def collect_evidence(source_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Collect read-only compliance evidence from a named source.

    For source_name="github", params must include owner, repo, and
    optionally branch (defaults to "main"). Checks branch protection and
    CODEOWNERS presence, maps results to control references, stores the
    full record in StateStore, and returns only an opaque collection_id —
    never the raw evidence.
    """
    if source_name != "github":
        return {"error": f"Unknown or unimplemented source: {source_name}"}

    owner = params.get("owner")
    repo = params.get("repo")
    branch = params.get("branch", "main")
    if not owner or not repo:
        return {"error": "params must include 'owner' and 'repo'."}

    record = collect_github_evidence(owner, repo, branch)
    collection_id = store.save(record)
    return {
        "collection_id": collection_id,
        "source": "github",
        "repository": f"{owner}/{repo}",
        "branch": branch,
    }


@mcp.tool()
def get_evidence_collection(collection_id: str) -> dict[str, Any]:
    """Retrieve a previously stored evidence collection by its opaque id."""
    record = store.get(collection_id)
    if record is None:
        return {"error": f"No evidence collection found for id: {collection_id}"}
    return record


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
