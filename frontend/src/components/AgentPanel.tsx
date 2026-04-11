import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface Agent {
    id: number;
    name: string;
    role: string;
    status: string;
    task_count: number;
}

interface Props {
    refreshTrigger: number;
}

const ROLE_EMOJI: Record<string, string> = {
    project_manager: '📋',
    ux_designer: '🎨',
    frontend_dev: '⚛️',
    backend_dev: '⚙️',
    fullstack: '🔧',
    research: '🔬',
    db_engineer: '🗄️',
};

export default function AgentPanel({ refreshTrigger }: Props) {
    const [agents, setAgents] = useState<Agent[]>([]);

    useEffect(() => {
        loadAgents();
    }, [refreshTrigger]);

    async function loadAgents() {
        try {
            const stats = await api.getStats();
            setAgents(stats.agent_summary || []);
        } catch (err) {
            console.error('Failed to load agents:', err);
        }
    }

    async function togglePause(agent: Agent) {
        try {
            const newStatus = agent.status === 'paused' ? 'idle' : 'paused';
            await api.updateAgent(agent.id, { status: newStatus });
            loadAgents();
        } catch (err) {
            console.error('Failed to update agent:', err);
        }
    }

    return (
        <div className="panel">
            <div className="panel-header">
                <h3>Team</h3>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {agents.length} agents
                </span>
            </div>
            <div className="agent-grid">
                {agents.map(agent => (
                    <div key={agent.id} className="agent-card">
                        <div className="agent-info">
                            <div className="agent-avatar">{ROLE_EMOJI[agent.role] || '🤖'}</div>
                            <div>
                                <div className="agent-name">{agent.name}</div>
                                <div className="agent-role">
                                    {agent.role.replace(/_/g, ' ')} · {agent.task_count} tasks
                                </div>
                            </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span className={`agent-status status-${agent.status}`}>{agent.status}</span>
                            <button
                                className="btn btn-ghost btn-sm"
                                onClick={() => togglePause(agent)}
                                title={agent.status === 'paused' ? 'Resume' : 'Pause'}
                            >
                                {agent.status === 'paused' ? '▶' : '⏸'}
                            </button>
                        </div>
                    </div>
                ))}
                {agents.length === 0 && (
                    <div className="empty-state">No agents registered</div>
                )}
            </div>
        </div>
    );
}
