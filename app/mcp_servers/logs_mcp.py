import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Logs and Monitoring MCP Server")

LOGS_DB = {
    "payment-service": [
        "[2026-07-01 16:10:05] ERROR ConnectionTimeout: Database connection pool exhausted. Max connections (100) reached.",
        "[2026-07-01 16:10:12] ERROR 504 GATEWAY TIMEOUT: GET /charge failed after 15000ms",
        "[2026-07-01 16:10:20] WARN RetryHandler: Retry attempt 1 failed for DB query.",
        "[2026-07-01 16:10:25] ERROR ConnectionTimeout: Database connection pool exhausted. Max connections (100) reached.",
        "[2026-07-01 16:10:35] ERROR 504 GATEWAY TIMEOUT: GET /charge failed after 15000ms",
    ],
    "user-service": [
        "[2026-07-01 16:15:00] INFO UploadHandler: Starting avatar upload for user-942",
        "[2026-07-01 16:15:02] ERROR S3ClientError: Access Denied (Status Code: 403; Error Code: AccessDenied)",
        "[2026-07-01 16:15:02] ERROR UploadHandler: Failed to store avatar in S3 bucket 'user-avatars-prod'. Reason: 403 Forbidden",
    ],
    "frontend-service": [
        "[2026-07-01 16:20:00] INFO StaticServer: Serving index.html",
        "[2026-07-01 16:20:01] ERROR StaticServer: Failed to compile template. Syntax error: Missing closing brace in bundle.js line 452.",
    ],
}

HEALTH_DB = {
    "payment-service": {
        "status": "Degraded",
        "cpu_usage": "92%",
        "memory_usage": "8.2 GB / 16 GB",
        "active_connections": 100,
        "database_connected": False,
        "details": "High database connection latency. Database connection pool is full (100/100 active connections).",
    },
    "user-service": {
        "status": "Healthy",
        "cpu_usage": "15%",
        "memory_usage": "2.4 GB / 8 GB",
        "active_connections": 12,
        "database_connected": True,
        "details": "Service is responsive. All health checks pass, but external S3 uploads are failing.",
    },
    "frontend-service": {
        "status": "Healthy",
        "cpu_usage": "5%",
        "memory_usage": "1.1 GB / 4 GB",
        "active_connections": 150,
        "database_connected": True,
        "details": "Web server is active, but UI assets are reporting loading issues.",
    },
}


@mcp.tool()
def fetch_service_logs(service_name: str, limit: int = 10) -> dict:
    """Fetch recent system logs for the specified service to aid troubleshooting.

    Args:
        service_name: Name of the service (e.g., payment-service, user-service, frontend-service).
        limit: Number of log lines to retrieve.
    """
    print(f"Logs MCP: fetch_service_logs called for {service_name}", file=sys.stderr)
    logs = LOGS_DB.get(service_name)
    if not logs:
        # Dynamically generate realistic logs for other enterprise services
        logs = [
            f"[2026-07-02 10:00:00] INFO {service_name}: Initializing context...",
            f"[2026-07-02 10:01:15] WARN {service_name}: Latency peak detected during connection handshake.",
            f"[2026-07-02 10:02:30] ERROR {service_name}: Internal request failed. Cause: Outage in dependency service.",
            f"[2026-07-02 10:03:00] ERROR {service_name}: API Connection Timeout (Status Code: 504).",
        ]
    return {"service": service_name, "logs": logs[-limit:]}


@mcp.tool()
def check_service_health(service_name: str) -> dict:
    """Perform a health check on the specified service to see its status, CPU, memory, and database connectivity.

    Args:
        service_name: Name of the service (e.g., payment-service, user-service, frontend-service).
    """
    print(f"Logs MCP: check_service_health called for {service_name}", file=sys.stderr)
    health = HEALTH_DB.get(service_name)
    if not health:
        # Dynamically generate realistic health details for other services
        health = {
            "status": "Degraded",
            "cpu_usage": "78%",
            "memory_usage": "4.5 GB / 8 GB",
            "active_connections": 45,
            "database_connected": True,
            "details": f"Service is active, but response times are elevated due to potential resource constraints or dependency timeout on {service_name} endpoint.",
        }
    return {"service": service_name, "health_details": health}


if __name__ == "__main__":
    mcp.run()
