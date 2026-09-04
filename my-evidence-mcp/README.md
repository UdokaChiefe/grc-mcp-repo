# grc-evidence-mcp

A read-only compliance evidence-collection MCP server for Claude Desktop.
Built with FastMCP over stdio, following the [BuildinginGRC step-by-step
build guide](https://github.com/LSDubose/my-evidence-mcp).

**Built with BuildinginGRC**

## The design rule

Read evidence **FROM** the audited system. Write evidence only **TO** the
local landing zone (a SQLite database). The audited system is never
modified — no settings are changed, nothing is created or deleted there.

## What it does

- **`list_evidence_sources`** — lists which evidence sources are available,
  flagging which are real and which are stub placeholders.
- **`collect_evidence(source_name, params)`** — for `source_name="github"`,
  checks branch protection and CODEOWNERS presence on a repository you
  specify (`owner`, `repo`, `branch`). Maps results to control references
  (SOC2, ISO27001) and stores the full record locally, returning only an
  opaque `collection_id` — never the raw evidence — back to the model.
- **`get_evidence_collection(collection_id)`** — retrieves a previously
  stored evidence record by its id.

The `collection_id` indirection matters: Claude never has to reproduce a
full evidence payload in conversation to reference it later, and the full
record stays in your local SQLite file, not in chat history.

## Setup

```bash
git clone <this-repo>
cd my-evidence-mcp
python -m venv venv

# Windows
venv\Scripts\pip install -e .

# macOS/Linux
venv/bin/pip install -e .
```

Create a **fine-grained GitHub personal access token**, scoped to only the
repository you'll test against, with just:

- `Administration: read`
- `Contents: read`

Then:

```bash
cp .env.example .env
# edit .env and set GITHUB_TOKEN=your_token_value_here
```

Add it to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "grc-evidence-mcp": {
      "command": "/full/path/to/venv/bin/python",
      "args": ["-m", "grc_evidence_mcp.server"]
    }
  }
}
```

Use the **full path** to the venv's Python — Claude Desktop does not
inherit your terminal's PATH. Fully quit and reopen Claude Desktop after
editing the config.

## Important limitation: GitHub 404s

GitHub's classic branch-protection endpoint and its newer Rulesets system
are separate backends. This project checks the newer
`/repos/{owner}/{repo}/rules/branches/{branch}` endpoint, which correctly
sees protection configured either way, and distinguishes a **confirmed**
absence (HTTP 200, empty rule list) from an **unconfirmed** one (a 404,
which usually means the repository itself wasn't found or the token
lacks access — not that protection is off).

For CODEOWNERS, a "not found" result checks only a few common paths
(root, `.github/`, `docs/`). It is a candidate finding, not a confirmed
gap — a human reviewer should verify before treating it as one.

**"No" and "I don't know" are not the same finding.** That distinction is
part of good GRC engineering, and this tool preserves it rather than
collapsing every negative result into a flat "missing."

## What an API result proves vs. what it doesn't

A confirmed API result reflects the state of the audited system at the
moment of the call. It is not a substitute for a full audit, does not
account for changes made after collection, and (for the GitHub source)
only checks two specific controls. Treat evidence collections as inputs
to a human review process, not as a final compliance determination.

## Repository structure

```
grc_evidence_mcp/
  __init__.py
  store.py     — SQLite-backed StateStore with opaque ids
  server.py    — MCP tool registration and evidence-storage workflow
  github.py    — read-only GitHub API evidence collector
.env.example   — safe template for the GitHub token variable
.gitignore     — keeps .env and local DB files out of version control
pyproject.toml — dependencies and entry point
```

## Core tools

`list_evidence_sources` · `collect_evidence` · `get_evidence_collection`
