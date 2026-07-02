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
# ruff: noqa: E402

import os

import google.auth
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

# Setup default GCP project environment if available
try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
except Exception:
    pass

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

# Determine model based on environment
use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "False").lower() == "true"
model_name = "gemini-2.5-flash"

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

# Initialize MCP Toolsets
# Note: we use 'uv run python' to execute local python MCP servers
jira_mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv", args=["run", "python", "app/mcp_servers/jira_mcp.py"]
        )
    )
)

logs_mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv", args=["run", "python", "app/mcp_servers/logs_mcp.py"]
        )
    )
)

kb_mcp_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv", args=["run", "python", "app/mcp_servers/kb_mcp.py"]
        )
    )
)

# 1. Ticket Analyzer Agent
ticket_analyzer = Agent(
    name="ticket_analyzer",
    model=model_name,
    description="Analyzes incident tickets in Jira, retrieves details, and identifies the affected service.",
    instruction="""You are a Ticket Analyzer.
Your task is to fetch and analyze details of the incident ticket (e.g. INC-101) from the Jira MCP.
Use the 'get_ticket_details' tool to load the ticket information.
Extract and output:
- The ticket ID
- The ticket Title and Description
- The affected Service name (e.g., payment-service, user-service, frontend-service)
- The Priority level
""",
    tools=[jira_mcp_toolset],
)

# 2. Log Analyzer Agent
log_analyzer = Agent(
    name="log_analyzer",
    model=model_name,
    description="Checks the real-time health and retrieves logs for services.",
    instruction="""You are a Systems and Log Analyzer.
Your task is to retrieve system logs and health status for the affected service using the Logs MCP.
Use 'check_service_health' to verify CPU, memory, and database connectivity.
Use 'fetch_service_logs' to get the latest error logs.
Analyze this data to pinpoint what is failing (e.g., database connection timeout, access denied, bundle syntax error) and report the exact symptoms.
""",
    tools=[logs_mcp_toolset],
)

# 3. RCA (Root Cause Analysis) Agent
rca_agent = Agent(
    name="rca_agent",
    model=model_name,
    description="Queries the Knowledge Base for runbooks and known issues matching incident symptoms.",
    instruction="""You are a Root Cause Analysis (RCA) Specialist.
Your task is to query the Knowledge Base MCP using 'search_runbooks' with relevant keywords (e.g., connection, S3, compile, timeout) matching the symptoms and logs.
Analyze the runbook recommendations and determine:
- What is the most likely root cause?
- Which runbook or SOP (Standard Operating Procedure) applies?
- What are the suggested remediation steps?
""",
    tools=[kb_mcp_toolset],
)

# 4. Resolution Planner Agent
planner_agent = Agent(
    name="planner_agent",
    model=model_name,
    description="Drafts a custom, step-by-step resolution plan for an incident.",
    instruction="""You are a Resolution Planner.
Your task is to draft a step-by-step remediation plan to resolve the incident based on the root cause and the recommended runbook steps.
Create a structured checklist containing:
- Immediate mitigation steps
- Environment config changes (if any)
- Verification steps to ensure the service returns to health

CRITICAL: Do NOT ask the user or the coordinator for permission, confirmation, or approval to proceed. Do NOT ask any questions. Present the checklist as a final plan so the coordinator can proceed to doc_agent immediately.
""",
    tools=[],
)

# 5. Documentation Agent
doc_agent = Agent(
    name="doc_agent",
    model=model_name,
    description="Updates ticket status in Jira and logs new runbook entries in the Knowledge Base.",
    instruction="""You are a Technical Documentation Agent.
Your task is to finalize the incident resolution:
1. Use 'update_ticket_status' in the Jira MCP to mark the incident ticket status as 'Resolved'. In the comment, include the summary of root cause and resolution.
2. Use 'add_kb_entry' in the KB MCP to save the new resolution steps so other engineers can find it.
3. Draft a final update report summarizing: ticket ID, root cause, resolution actions taken, and KB entry ID.
""",
    tools=[jira_mcp_toolset, kb_mcp_toolset],
)

# 6. Coordinator Agent (Root Agent)
coordinator = Agent(
    name="coordinator",
    model=model_name,
    description="Orchestrates the incident resolution workflow by delegating to specialist sub-agents.",
    instruction="""You are the Lead Incident Resolution Coordinator for our Enterprise AI Incident Management Platform.
Your goal is to coordinate the analysis and resolution of incoming incident tickets across a wide catalog of enterprise services.
You have a team of specialist sub-agents: ticket_analyzer, log_analyzer, rca_agent, planner_agent, and doc_agent.

You MUST sequentially, strictly, and without exception execute all 5 of the following steps:
1. Delegate to 'ticket_analyzer' to get the details of the incident ticket (e.g. INC-101) and identify the service.
2. Delegate to 'log_analyzer' to check the health and logs of that service.
3. Delegate to 'rca_agent' to match symptoms against KB runbooks and identify the root cause.
4. Delegate to 'planner_agent' to draft the step-by-step resolution checklist.
5. Delegate to 'doc_agent' to resolve the ticket in Jira, add a comment, and document the resolution in the KB.

CRITICAL SIMULATION RULES:
- You are running in fully automated mode. Do NOT ask the user or any agent for permission, confirmation, or approval. Do NOT ask questions or present choices.
- In this SRE simulation, the proposed remediation plan from 'planner_agent' is assumed to be automatically approved and executed immediately. You do not need to wait for or perform external execution.
- Therefore, as soon as 'planner_agent' returns the checklist, you MUST immediately delegate to 'doc_agent' to mark the incident ticket as 'Resolved' in Jira and log the new entry in the Knowledge Base.
- You must NEVER stop after the planner_agent or output your final report without first delegating to 'doc_agent' and receiving its resolution report.

FINAL RESPONSE FORMAT REQUIREMENT:
When presenting your final postmortem summary to the user, you MUST follow this exact Markdown structure without fail:

# INCIDENT SUMMARY: [Ticket ID]

## 📋 INCIDENT OWNERSHIP & METADATA
- **Primary Owner**: [e.g. Frontend Team, Auth Team, Database Ops, Security Ops]
- **Responsible Team**: [e.g. Identity Team, Payment Gateway Team, Platform Eng]
- **Escalation Team**: [e.g. Platform Engineering, Cloud Infrastructure, Security Response]
- **Severity**: [Low / Medium / High / Critical]
- **Suggested Priority**: [Suggested Priority]
- **Estimated Resolution Time (ETA)**: [e.g. 15 minutes, 30 minutes, 1 hour]
- **Business Impact**: [Describe the business effect of the outage]
- **Customer Impact**: [Describe what end-users are experiencing]

---

## 👥 BUSINESS & USER-FRIENDLY RESPONSE (For Customers & Stakeholders)
- **What Happened**: [Describe in plain, simple English]
- **Why It Happened**: [Explain in simple words without coding jargon]
- **Current Impact & Actions**: [Detail what the team is doing]
- **Expected Resolution**: [ETA and workaround options, if any]
- **Customer Action Required**: [Yes/No/None]

---

## 💻 TECHNICAL RESPONSE (For Engineers)
- **Predicted Root Cause**: [Technical explanation, e.g. IAM permission mismatch, connection pool leak]
- **Logs Analysed**: [Technical logs or metrics analysed]
- **Configuration Changes & Remediation**: [Code-level settings or configuration modifications required]
- **Suggested Troubleshooting & Rollback Commands**: [Commands to run, git rollbacks, service restarts]
""",
    sub_agents=[ticket_analyzer, log_analyzer, rca_agent, planner_agent, doc_agent],
)

root_agent = coordinator

app = App(
    root_agent=root_agent,
    name="app",
)
