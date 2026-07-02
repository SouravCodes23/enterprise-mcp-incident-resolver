// State Management
let tickets = [];
let selectedTicket = null;

// Tab Routing
const navItems = document.querySelectorAll('.nav-item');
const tabContents = document.querySelectorAll('.tab-content');

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const tabId = item.getAttribute('data-tab');
        
        // Update menu active class
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        
        // Show correct content
        tabContents.forEach(content => {
            if (content.id === tabId) {
                content.classList.add('active-content');
            } else {
                content.classList.remove('active-content');
            }
        });

        // Custom tab loading actions
        if (tabId === 'dashboard-tab') {
            loadTickets();
        } else if (tabId === 'kb-tab') {
            loadKB();
        }

        // Update header subtitle
        updateHeader(tabId);
    });
});

function updateHeader(tabId) {
    const title = document.getElementById('page-title');
    const subtitle = document.getElementById('page-subtitle');
    
    if (tabId === 'dashboard-tab') {
        title.innerText = "Incidents Dashboard";
        subtitle.innerText = "Monitor and resolve active system outages with Google ADK agents";
    } else if (tabId === 'new-ticket-tab') {
        title.innerText = "Report System Incident";
        subtitle.innerText = "File a new ticket into the Jira tracker to trigger investigation";
    } else if (tabId === 'kb-tab') {
        title.innerText = "Operations Knowledge Base";
        subtitle.innerText = "Standard Operating Procedures (SOPs) and historical runbooks";
    }
}

// Load tickets from FastAPI
async function loadTickets() {
    const listContainer = document.getElementById('ticket-list-container');
    const countBadge = document.getElementById('ticket-count');
    
    try {
        const response = await fetch('/api/incidents');
        tickets = await response.json();
        
        countBadge.innerText = `${tickets.length} Tickets`;
        listContainer.innerHTML = '';
        
        if (tickets.length === 0) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-circle-check"></i>
                    <h3>No Active Incidents</h3>
                    <p>All systems operational. Good job!</p>
                </div>
            `;
            return;
        }

        tickets.forEach(ticket => {
            const card = document.createElement('div');
            card.className = `ticket-card ${selectedTicket && selectedTicket.id === ticket.id ? 'selected' : ''}`;
            card.innerHTML = `
                <div class="ticket-card-header">
                    <span class="ticket-id">${ticket.id}</span>
                    <span class="priority-badge priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span>
                </div>
                <div class="ticket-title">${ticket.title}</div>
                <div class="ticket-footer">
                    <span class="ticket-service"><i class="fa-solid fa-server"></i> ${ticket.service}</span>
                    <span class="status-badge status-${ticket.status.toLowerCase()}">${ticket.status}</span>
                </div>
            `;
            
            card.addEventListener('click', () => {
                // Select card
                document.querySelectorAll('.ticket-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
                selectTicket(ticket);
            });
            
            listContainer.appendChild(card);
        });

        // Re-draw selected ticket details if it was updated
        if (selectedTicket) {
            const updated = tickets.find(t => t.id === selectedTicket.id);
            if (updated) {
                updateSelectedTicketUI(updated);
            }
        }
    } catch (e) {
        console.error("Error fetching tickets:", e);
        listContainer.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error loading incidents</h3></div>`;
    }
}

// Update selected ticket details in-place without clearing the timeline panel
function updateSelectedTicketUI(ticket) {
    selectedTicket = ticket;
    
    // Update status badge
    const badge = document.querySelector('.detail-title-row .status-badge');
    if (badge) {
        badge.className = `status-badge status-${ticket.status.toLowerCase()}`;
        badge.innerText = ticket.status;
    }
    
    // Update comments
    const commentsContainer = document.getElementById('comments-container');
    if (commentsContainer) {
        commentsContainer.innerHTML = (ticket.comments && ticket.comments.length > 0)
            ? ticket.comments.map(c => `<div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; font-size: 12px; line-height: 1.4">${c}</div>`).join('')
            : '<span style="font-size: 12px; color: var(--text-muted)">No updates recorded in Jira.</span>';
    }
    
    // Update resolve button
    const resolveBtn = document.getElementById('btn-resolve-incident');
    if (resolveBtn) {
        resolveBtn.disabled = (ticket.status === 'Resolved');
        if (ticket.status === 'Resolved') {
            resolveBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Incident Resolved`;
        } else {
            resolveBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Resolve with Multi-Agents`;
        }
    }
    
    // Update reset button
    const resetBtn = document.getElementById('btn-reset-incident');
    if (resetBtn) {
        resetBtn.style.display = (ticket.status === 'Resolved' || ticket.status === 'Unresolved') ? 'inline-flex' : 'none';
        resetBtn.disabled = false;
        resetBtn.innerHTML = `<i class="fa-solid fa-arrow-rotate-left"></i> Reset`;
    }
}

// Select a ticket to display in Detail Panel
function selectTicket(ticket) {
    selectedTicket = ticket;
    const detailPanel = document.getElementById('incident-detail-panel');
    
    detailPanel.innerHTML = `
        <div class="detail-layout">
            <div class="detail-header">
                <div class="detail-title-row">
                    <h2>${ticket.title}</h2>
                    <span class="status-badge status-${ticket.status.toLowerCase()}">${ticket.status}</span>
                </div>
                <div class="detail-meta-row">
                    <span><strong>ID:</strong> ${ticket.id}</span>
                    <span><strong>Service:</strong> <code style="font-family: var(--font-mono); color: var(--primary-color)">${ticket.service}</code></span>
                    <span><strong>Priority:</strong> ${ticket.priority}</span>
                </div>
            </div>
            
            <div class="detail-body">
                <div class="detail-sidebar">
                    <div class="description-block">
                        <h4>Incident Description</h4>
                        <p>${ticket.description}</p>
                    </div>
                    
                    <div class="action-block" style="display: flex; gap: 10px;">
                        <button class="btn btn-primary" id="btn-resolve-incident" ${ticket.status === 'Resolved' ? 'disabled' : ''} style="flex: 1">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> 
                            ${ticket.status === 'Resolved' ? 'Incident Resolved' : 'Resolve with Multi-Agents'}
                        </button>
                        <button class="btn btn-secondary" id="btn-reset-incident" style="flex: 0 0 auto; display: ${(ticket.status === 'Resolved' || ticket.status === 'Unresolved') ? 'inline-flex' : 'none'};">
                            <i class="fa-solid fa-arrow-rotate-left"></i> Reset
                        </button>
                    </div>

                    <div class="comments-block" style="margin-top: 10px;">
                        <h4 style="font-size: 13px; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 10px;">Jira Logs & Comments</h4>
                        <div id="comments-container" style="display: flex; flex-direction: column; gap: 10px; max-height: 250px; overflow-y: auto;">
                            ${(ticket.comments && ticket.comments.length > 0) 
                                ? ticket.comments.map(c => `<div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; font-size: 12px; line-height: 1.4">${c}</div>`).join('') 
                                : '<span style="font-size: 12px; color: var(--text-muted)">No updates recorded in Jira.</span>'}
                        </div>
                    </div>
                </div>
                
                <div class="detail-main">
                    <div class="timeline-section">
                        <div class="timeline-header">
                            <h3><i class="fa-solid fa-network-wired"></i> Agent Execution Timeline</h3>
                            <span id="timeline-status" style="font-size: 12px; color: var(--text-secondary)">Idle</span>
                        </div>
                        <div class="timeline-flow" id="timeline-container">
                            <div class="empty-state" style="padding: 30px;">
                                <i class="fa-solid fa-bolt" style="font-size: 28px;"></i>
                                <p style="font-size: 12px; margin-top: 8px;">Trigger the multi-agent system to see diagnostic metrics, runbook fetches, and status logs in real-time.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.getElementById('btn-resolve-incident').addEventListener('click', () => {
        triggerIncidentResolution(ticket.id);
    });

    const resetBtn = document.getElementById('btn-reset-incident');
    if (resetBtn) {
        resetBtn.addEventListener('click', async () => {
            resetBtn.disabled = true;
            resetBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
            try {
                const response = await fetch(`/api/incidents/${ticket.id}/reset`, { method: 'POST' });
                if (response.ok) {
                    await loadTickets();
                }
            } catch (e) {
                console.error("Error resetting incident:", e);
                resetBtn.disabled = false;
                resetBtn.innerHTML = `<i class="fa-solid fa-arrow-rotate-left"></i> Reset`;
            }
        });
    }
}

// Trigger Agent Resolution SSE stream
async function triggerIncidentResolution(ticketId) {
    const resolveBtn = document.getElementById('btn-resolve-incident');
    const timelineContainer = document.getElementById('timeline-container');
    const timelineStatus = document.getElementById('timeline-status');
    
    // Setup UI
    resolveBtn.disabled = true;
    resolveBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Agents Working...`;
    timelineContainer.innerHTML = '';
    timelineStatus.innerHTML = `<span style="color: var(--primary-color)"><i class="fa-solid fa-gear fa-spin"></i> Coordinating Agents...</span>`;

    try {
        const response = await fetch('/run_sse', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_name: 'app',
                user_id: 'default_user',
                session_id: ticketId,
                new_message: {
                    role: 'user',
                    parts: [
                        { text: `Please analyze and resolve incident ticket ${ticketId}` }
                    ]
                },
                streaming: true
            })
        });

        if (!response.ok) {
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let hasError = false;
        let errorMessage = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop(); // save incomplete line

            for (const line of lines) {
                if (line.trim().startsWith('data: ')) {
                    const eventJson = line.trim().substring(6);
                    try {
                        const event = JSON.parse(eventJson);
                        if (event.error) {
                            hasError = true;
                            errorMessage = event.error;
                        }
                        renderAgentEvent(event);
                    } catch (e) {
                        console.error("Error parsing event JSON:", e);
                    }
                }
            }
        }
        
        if (!hasError) {
            timelineStatus.innerHTML = `<span style="color: var(--success-color)"><i class="fa-solid fa-circle-check"></i> Resolution Complete</span>`;
            resolveBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i> Resolved`;
            
            // Persist Resolved status in backend
            try {
                await fetch(`/api/incidents/${ticketId}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        status: 'Resolved',
                        comment: 'Incident resolution workflow completed successfully.'
                    })
                });
            } catch (err) {
                console.error("Failed to update status on success:", err);
            }
            
            // Refresh Jira ticket list and details to show new status and comments
            setTimeout(async () => {
                await loadTickets();
            }, 1000);
        } else {
            // Persist Unresolved status in backend
            try {
                await fetch(`/api/incidents/${ticketId}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        status: 'Unresolved',
                        comment: `Workflow failed: ${errorMessage || 'Agent execution was interrupted or failed to find a valid solution.'}`
                    })
                });
            } catch (err) {
                console.error("Failed to update status on error:", err);
            }
            
            setTimeout(async () => {
                await loadTickets();
            }, 1000);
        }

    } catch (e) {
        console.error("Resolution flow error:", e);
        timelineStatus.innerHTML = `<span style="color: var(--danger-color)"><i class="fa-solid fa-triangle-exclamation"></i> Error during resolution</span>`;
        resolveBtn.disabled = false;
        resolveBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Try Again`;
        
        const errorNode = document.createElement('div');
        errorNode.className = 'timeline-node';
        errorNode.innerHTML = `
            <div class="node-icon" style="border-color: var(--danger-color); color: var(--danger-color)">
                <i class="fa-solid fa-circle-xmark"></i>
            </div>
            <div class="node-content" style="border-color: rgba(239, 68, 68, 0.2)">
                <div class="node-header">
                    <span class="node-author" style="color: var(--danger-color)">System Error</span>
                </div>
                <div class="node-text">The multi-agent workflow encountered an issue: ${e.message}</div>
            </div>
        `;
        timelineContainer.appendChild(errorNode);
        
        // Persist Unresolved status in backend
        try {
            await fetch(`/api/incidents/${ticketId}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: 'Unresolved',
                    comment: `Resolution flow crashed: ${e.message}`
                })
            });
        } catch (err) {
            console.error("Failed to update status on crash:", err);
        }
        
        setTimeout(async () => {
            await loadTickets();
        }, 1000);
    }
}

// Render individual agent event to timeline
function renderAgentEvent(event) {
    const container = document.getElementById('timeline-container');
    if (!container) return;

    // Clear empty state if present
    if (container.querySelector('.empty-state')) {
        container.innerHTML = '';
    }

    // Handle backend stream errors (like 429 rate limit errors)
    if (event.error) {
        const timelineStatus = document.getElementById('timeline-status');
        const resolveBtn = document.getElementById('btn-resolve-incident');
        
        timelineStatus.innerHTML = `<span style="color: var(--danger-color)"><i class="fa-solid fa-triangle-exclamation"></i> Error during resolution</span>`;
        if (resolveBtn) {
            resolveBtn.disabled = false;
            resolveBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Try Again`;
        }

        const errorNode = document.createElement('div');
        errorNode.className = 'timeline-node';
        errorNode.innerHTML = `
            <div class="node-icon" style="border-color: var(--danger-color); color: var(--danger-color)">
                <i class="fa-solid fa-circle-xmark"></i>
            </div>
            <div class="node-content" style="border-color: rgba(239, 68, 68, 0.2)">
                <div class="node-header">
                    <span class="node-author" style="color: var(--danger-color)">System Error</span>
                </div>
                <div class="node-text">${event.error}</div>
            </div>
        `;
        container.appendChild(errorNode);
        return;
    }

    const author = event.author || 'system';
    
    // Skip formatting empty events
    if (author === 'user') return;

    // Render LLM output text
    let textContent = '';
    if (event.content && event.content.parts) {
        textContent = event.content.parts
            .map(p => {
                if (p.text) return p.text;
                const fCall = p.functionCall || p.function_call;
                if (fCall && fCall.name === 'transfer_to_agent') {
                    const target = fCall.args ? fCall.args.agent_name : '';
                    return `[Transferring coordination to specialist: ${target}]`;
                }
                return '';
            })
            .filter(Boolean)
            .join('\n');
    }

    // Render Tool Calls or Tool Responses
    let detailsHtml = '';
    let isToolNode = false;
    
    if (event.actions) {
        const toolCalls = event.actions.toolCalls || event.actions.tool_calls;
        const toolResponses = event.actions.toolResponses || event.actions.tool_responses;

        if (toolCalls && toolCalls.length > 0) {
            isToolNode = true;
            toolCalls.forEach(tc => {
                const fCall = tc.functionCall || tc.function_call;
                const name = fCall ? fCall.name : 'Unknown Tool';
                const args = fCall ? JSON.stringify(fCall.args, null, 2) : '';
                detailsHtml += `
                    <div style="margin-bottom: 8px;">
                        <span style="color: var(--warning-color); font-weight: 600"><i class="fa-solid fa-screwdriver-wrench"></i> Invoking Tool:</span> 
                        <code style="color: var(--text-primary)">${name}</code>
                        ${args ? `<pre style="margin-top: 4px; padding: 6px; background: rgba(0,0,0,0.3); border-radius: 4px; overflow-x: auto">${args}</pre>` : ''}
                    </div>
                `;
            });
        }
        
        if (toolResponses && toolResponses.length > 0) {
            isToolNode = true;
            toolResponses.forEach(tr => {
                const fResp = tr.functionResponse || tr.function_response;
                const responseText = fResp ? JSON.stringify(fResp.response || fResp.output, null, 2) : '';
                detailsHtml += `
                    <div>
                        <span style="color: var(--success-color); font-weight: 600"><i class="fa-solid fa-reply"></i> Tool Response:</span>
                        <pre style="margin-top: 4px; padding: 6px; background: rgba(0,0,0,0.3); border-radius: 4px; overflow-x: auto; max-height: 200px">${responseText}</pre>
                    </div>
                `;
            });
        }
    }

    // Don't show text-only events that are completely empty
    if (!textContent && !detailsHtml) return;

    const node = document.createElement('div');
    node.className = 'timeline-node';

    // Determine icons
    let iconClass = 'fa-solid fa-robot';
    let activeClass = '';
    if (author === 'coordinator') {
        iconClass = 'fa-solid fa-user-tie';
        activeClass = 'active';
    } else if (author === 'ticket_analyzer') {
        iconClass = 'fa-solid fa-magnifying-glass';
    } else if (author === 'log_analyzer') {
        iconClass = 'fa-solid fa-terminal';
    } else if (author === 'rca_agent') {
        iconClass = 'fa-solid fa-brain';
    } else if (author === 'planner_agent') {
        iconClass = 'fa-solid fa-clipboard-list';
    } else if (author === 'doc_agent') {
        iconClass = 'fa-solid fa-file-pen';
        activeClass = 'success';
    }

    if (isToolNode && !textContent) {
        iconClass = 'fa-solid fa-gears';
        activeClass = 'tool';
    }

    const timeString = new Date().toLocaleTimeString();

    node.innerHTML = `
        <div class="node-icon ${activeClass}">
            <i class="${iconClass}"></i>
        </div>
        <div class="node-content">
            <div class="node-header">
                <span class="node-author" style="color: ${author === 'coordinator' ? 'var(--primary-color)' : 'var(--text-primary)'}">
                    ${author.replace('_', ' ')}
                </span>
                <span class="node-time">${timeString}</span>
            </div>
            ${textContent ? `<div class="node-text">${formatMarkdown(textContent)}</div>` : ''}
            ${detailsHtml ? `<div class="node-details">${detailsHtml}</div>` : ''}
        </div>
    `;

    container.appendChild(node);
    container.scrollTop = container.scrollHeight;
}

// Simple markdown formatter helper
function formatMarkdown(text) {
    // Escapes HTML tags
    let formatted = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    
    // Bold **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Bullet points
    formatted = formatted.replace(/^\s*-\s+(.*?)$/gm, '<li>$1</li>');
    formatted = formatted.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
    
    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

// Handle Form Submission
const createForm = document.getElementById('create-incident-form');
createForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const title = document.getElementById('ticket-title').value;
    const service = document.getElementById('ticket-service').value;
    const priority = document.getElementById('ticket-priority').value;
    const description = document.getElementById('ticket-description').value;

    try {
        const response = await fetch('/api/incidents', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ title, service, priority, description })
        });
        
        if (response.ok) {
            createForm.reset();
            // Switch to Dashboard Tab
            document.getElementById('nav-dashboard').click();
        } else {
            alert('Failed to report incident.');
        }
    } catch (e) {
        console.error("Form error:", e);
        alert('Connection error filing ticket.');
    }
});

// Load Knowledge Base
async function loadKB() {
    const kbContainer = document.getElementById('kb-entries-container');
    try {
        const response = await fetch('/api/kb');
        const entries = await response.json();
        
        renderKB(entries);
    } catch (e) {
        console.error("KB error:", e);
        kbContainer.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Error loading KB</h3></div>`;
    }
}

function renderKB(entries) {
    const kbContainer = document.getElementById('kb-entries-container');
    kbContainer.innerHTML = '';
    
    if (entries.length === 0) {
        kbContainer.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1">
                <i class="fa-solid fa-circle-question"></i>
                <h3>No KB Articles Found</h3>
                <p>Knowledge base is empty. Entries are added when incidents are resolved.</p>
            </div>
        `;
        return;
    }

    entries.forEach(entry => {
        const card = document.createElement('div');
        card.className = 'kb-card';
        card.innerHTML = `
            <div class="kb-card-header">
                <h3>${entry.title}</h3>
                <span class="kb-service-tag">${entry.service}</span>
            </div>
            <div class="kb-steps">${entry.steps}</div>
            <div class="kb-tags">
                <span class="tag">ID: ${entry.id}</span>
                ${entry.keywords ? entry.keywords.map(kw => `<span class="tag">${kw}</span>`).join('') : ''}
            </div>
        `;
        kbContainer.appendChild(card);
    });
}

// Search KB Action
document.getElementById('btn-search-kb').addEventListener('click', performKBSearch);
document.getElementById('kb-search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        performKBSearch();
    }
});

async function performKBSearch() {
    const query = document.getElementById('kb-search-input').value;
    const kbContainer = document.getElementById('kb-entries-container');
    kbContainer.innerHTML = '<div class="loading-state"><i class="fa-solid fa-spinner fa-spin"></i> Searching Knowledge Base...</div>';

    try {
        const response = await fetch(`/api/kb?query=${encodeURIComponent(query)}`);
        const entries = await response.json();
        renderKB(entries);
    } catch (e) {
        console.error("Search error:", e);
        kbContainer.innerHTML = `<div class="empty-state"><i class="fa-solid fa-triangle-exclamation"></i><h3>Search Failed</h3></div>`;
    }
}

// Refresh buttons
document.getElementById('btn-refresh-tickets').addEventListener('click', () => {
    loadTickets();
    if (document.getElementById('kb-tab').classList.contains('active-content')) {
        loadKB();
    }
});

// App Startup
loadTickets();
