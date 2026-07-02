import json
import os
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Knowledge Base MCP Server")

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "kb_entries.json"
)


def load_kb() -> list:
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"KB MCP Error loading entries: {e}", file=sys.stderr)
    return []


def save_kb(entries: list):
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception as e:
        print(f"KB MCP Error saving entries: {e}", file=sys.stderr)


@mcp.tool()
def search_runbooks(query: str) -> dict:
    """Search the Knowledge Base for runbooks and SOPs matching keywords.

    Args:
        query: Search term (e.g., pool, s3, connection, frontend, timeout).
    """
    print(f"KB MCP: search_runbooks called with query='{query}'", file=sys.stderr)
    q = query.lower()
    entries = load_kb()
    results = []
    for runbook in entries:
        if (
            q in runbook["title"].lower()
            or q in runbook["steps"].lower()
            or any(q in kw.lower() for kw in runbook.get("keywords", []))
        ):
            results.append(runbook)
    return {"query": query, "results": results}


@mcp.tool()
def add_kb_entry(title: str, service: str, steps: str) -> dict:
    """Add a new resolution runbook entry to the Knowledge Base.

    Args:
        title: Title of the new runbook (e.g., Payment service DB connection fix).
        service: Affected service name (e.g., payment-service).
        steps: Step-by-step resolution steps.
    """
    print(
        f"KB MCP: add_kb_entry called for service={service}, title='{title}'",
        file=sys.stderr,
    )
    entries = load_kb()
    new_id = f"KB-{len(entries) + 1:03d}"
    keywords = list({w.strip(",.()\"'").lower() for w in title.split() if len(w) > 3})
    entry = {
        "id": new_id,
        "title": title,
        "service": service,
        "keywords": keywords,
        "steps": steps,
    }
    entries.append(entry)
    save_kb(entries)
    return {"status": "success", "kb_entry": entry}


if __name__ == "__main__":
    mcp.run()
