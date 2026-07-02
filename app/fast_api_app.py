# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging
import os

import google.auth
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app
from pydantic import BaseModel

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

# Setup standard fallback logging
logging.basicConfig(level=logging.INFO)
sys_logger = logging.getLogger("incident_resolver")

setup_telemetry()

# Handle optional Google Cloud Logging
try:
    _, project_id = google.auth.default()
    from google.cloud import logging as google_cloud_logging

    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger(__name__)
except Exception as e:
    sys_logger.warning(
        f"Could not initialize Google Cloud Logging: {e}. Falling back to standard logging."
    )

    class FallbackLogger:
        def log_struct(self, data, severity="INFO"):
            sys_logger.info(f"[{severity}] {data}")

    logger = FallbackLogger()

allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
session_service_uri = None
artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    otel_to_cloud=False,
    auto_create_session=True,
)
app.title = "incident-resolver"
app.description = "API for interacting with the Agent incident-resolver"

# File database paths
JIRA_DB = os.path.join(AGENT_DIR, "app", "data", "jira_tickets.json")
KB_DB = os.path.join(AGENT_DIR, "app", "data", "kb_entries.json")


class IncidentCreate(BaseModel):
    title: str
    service: str
    description: str
    priority: str


@app.get("/api/incidents")
def list_incidents():
    try:
        if os.path.exists(JIRA_DB):
            with open(JIRA_DB, encoding="utf-8") as f:
                return list(json.load(f).values())
    except Exception as e:
        sys_logger.error(f"Error reading Jira database: {e}")
    return []


@app.post("/api/incidents")
def create_incident(incident: IncidentCreate):
    try:
        tickets = {}
        if os.path.exists(JIRA_DB):
            with open(JIRA_DB, encoding="utf-8") as f:
                tickets = json.load(f)

        # Find next ID
        num = 101
        while f"INC-{num}" in tickets:
            num += 1
        ticket_id = f"INC-{num}"

        new_ticket = {
            "id": ticket_id,
            "title": incident.title,
            "service": incident.service,
            "description": incident.description,
            "priority": incident.priority,
            "status": "Open",
            "comments": [],
        }
        tickets[ticket_id] = new_ticket
        with open(JIRA_DB, "w", encoding="utf-8") as f:
            json.dump(tickets, f, indent=2)
        return new_ticket
    except Exception as e:
        sys_logger.error(f"Error writing to Jira database: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/incidents/{ticket_id}/reset")
def reset_incident(ticket_id: str):
    try:
        tickets = {}
        if os.path.exists(JIRA_DB):
            with open(JIRA_DB, encoding="utf-8") as f:
                tickets = json.load(f)
        if ticket_id in tickets:
            tickets[ticket_id]["status"] = "Open"
            tickets[ticket_id]["comments"] = []
            with open(JIRA_DB, "w", encoding="utf-8") as f:
                json.dump(tickets, f, indent=2)
            return tickets[ticket_id]
        else:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    except Exception as e:
        sys_logger.error(f"Error resetting Jira ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


class StatusUpdate(BaseModel):
    status: str
    comment: str | None = None


@app.post("/api/incidents/{ticket_id}/status")
def update_incident_status(ticket_id: str, payload: StatusUpdate):
    try:
        tickets = {}
        if os.path.exists(JIRA_DB):
            with open(JIRA_DB, encoding="utf-8") as f:
                tickets = json.load(f)
        if ticket_id in tickets:
            tickets[ticket_id]["status"] = payload.status
            if payload.comment:
                if "comments" not in tickets[ticket_id]:
                    tickets[ticket_id]["comments"] = []
                tickets[ticket_id]["comments"].append(payload.comment)
            with open(JIRA_DB, "w", encoding="utf-8") as f:
                json.dump(tickets, f, indent=2)
            return tickets[ticket_id]
        else:
            raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    except Exception as e:
        sys_logger.error(f"Error updating Jira ticket status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/kb")
def list_kb_entries(query: str | None = None):
    try:
        if os.path.exists(KB_DB):
            with open(KB_DB, encoding="utf-8") as f:
                entries = json.load(f)
                if query:
                    q = query.lower()
                    entries = [
                        e
                        for e in entries
                        if q in e["title"].lower()
                        or q in e["steps"].lower()
                        or any(q in kw.lower() for kw in e.get("keywords", []))
                    ]
                return entries
    except Exception as e:
        sys_logger.error(f"Error reading KB database: {e}")
    return []


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Serve static dashboard
FRONTEND_DIR = os.path.join(AGENT_DIR, "app", "frontend")

# Remove default "/" redirect route if present to serve our custom frontend
app.routes[:] = [r for r in app.routes if r.path != "/"]


@app.get("/")
@app.head("/")
def read_root():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Frontend Source Not Found</h1>")


# Mount frontend directory for static assets (CSS, JS)
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
