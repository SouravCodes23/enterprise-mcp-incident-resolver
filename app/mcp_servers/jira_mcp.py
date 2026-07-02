import json
import os
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Jira MCP Server")

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "jira_tickets.json"
)


def load_tickets() -> dict:
    try:
        if os.path.exists(DB_PATH):
            with open(DB_PATH, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Jira MCP Error loading tickets: {e}", file=sys.stderr)
    return {}


def save_tickets(tickets: dict):
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2)
    except Exception as e:
        print(f"Jira MCP Error saving tickets: {e}", file=sys.stderr)


@mcp.tool()
def get_ticket_details(ticket_id: str) -> dict:
    """Get the details of an incident ticket from Jira.

    Args:
        ticket_id: The ID of the incident ticket (e.g., INC-101).
    """
    print(f"Jira MCP: get_ticket_details called for {ticket_id}", file=sys.stderr)
    tickets = load_tickets()
    ticket = tickets.get(ticket_id)
    if not ticket:
        return {"error": f"Ticket {ticket_id} not found."}
    return ticket


@mcp.tool()
def update_ticket_status(ticket_id: str, status: str, comment: str) -> dict:
    """Update the status and add a comment to an incident ticket in Jira.

    Args:
        ticket_id: The ID of the incident ticket (e.g., INC-101).
        status: The new status of the ticket (e.g., Investigating, In Progress, Resolved).
        comment: A detailed comment detailing the current investigation or resolution.
    """
    print(
        f"Jira MCP: update_ticket_status called for {ticket_id} (status={status})",
        file=sys.stderr,
    )
    tickets = load_tickets()
    ticket = tickets.get(ticket_id)
    if not ticket:
        return {"error": f"Ticket {ticket_id} not found."}
    ticket["status"] = status
    if "comments" not in ticket:
        ticket["comments"] = []
    ticket["comments"].append(comment)
    tickets[ticket_id] = ticket
    save_tickets(tickets)
    return {"status": "success", "ticket": ticket}


@mcp.tool()
def list_all_tickets() -> list[dict]:
    """Retrieve all open and active incident tickets in Jira."""
    print("Jira MCP: list_all_tickets called", file=sys.stderr)
    tickets = load_tickets()
    return list(tickets.values())


if __name__ == "__main__":
    mcp.run()
