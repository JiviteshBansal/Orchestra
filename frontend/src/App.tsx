import { useState, useEffect, useRef } from 'react';
import { api } from './api/client';
import TaskBoard from './components/TaskBoard';
import AgentFeed from './components/AgentFeed';
import AgentPanel from './components/AgentPanel';
import ArtifactViewer from './components/ArtifactViewer';

interface Stats {
    total_tasks: number;
    task_counts: Record<string, number>;
    total_artifacts: number;
    total_prs: number;
    total_logs: number;
    llm_telemetry: { total_calls: number; avg_latency_ms?: number };
    ace_stats: { playbook_count: number; decision_count: number };
}

interface Toast {
    message: string;
    type: 'success' | 'error' | 'info';
}

interface ProgressEntry {
    stage: string;
    message: string;
    timestamp: string;
}

const STAT_CARDS = [
    { key: 'total', label: 'Tasks', variant: '' },
    { key: 'progress', label: 'In Progress', variant: 'info' },
    { key: 'review', label: 'In Review', variant: '' },
    { key: 'done', label: 'Completed', variant: 'success' },
    { key: 'artifacts', label: 'Artifacts', variant: '' },
    { key: 'llm', label: 'LLM Calls', variant: 'info' },
    { key: 'playbooks', label: 'Playbooks', variant: 'success' },
] as const;

const STAGE_ICONS: Record<string, string> = {
    planning: '📋',
    planned: '✅',
    executing: '⚡',
    reviewing: '🔍',
    completed: '🎉',
    error: '❌',
};

export default function App() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [requestText, setRequestText] = useState('');
    const [projectName, setProjectName] = useState('default');
    const [submitting, setSubmitting] = useState(false);
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [toast, setToast] = useState<Toast | null>(null);
    const [pipelineProgress, setPipelineProgress] = useState<ProgressEntry[]>([]);
    const [pipelineStatus, setPipelineStatus] = useState<string>('');
    const progressEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        loadStats();
    }, [refreshTrigger]);

    useEffect(() => {
        if (toast) {
            const t = setTimeout(() => setToast(null), 4000);
            return () => clearTimeout(t);
        }
    }, [toast]);

    // Auto-scroll progress log
    useEffect(() => {
        progressEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [pipelineProgress]);

    async function loadStats() {
        try {
            const data = await api.getStats();
            setStats(data);
        } catch (err) {
            console.error('Stats load failed:', err);
        }
    }

    function showToast(message: string, type: Toast['type'] = 'info') {
        setToast({ message, type });
    }

    function refresh() {
        setRefreshTrigger(prev => prev + 1);
    }

    async function handleSubmitRequest() {
        if (!requestText.trim()) return;
        setSubmitting(true);
        setPipelineProgress([]);
        setPipelineStatus('planning');

        setPipelineProgress(prev => [...prev, {
            stage: 'planning',
            message: 'Submitting request to Project Manager...',
            timestamp: new Date().toISOString(),
        }]);

        try {
            const result = await api.submitRequest(requestText, projectName);

            // The result now includes progress from the full pipeline
            if (result.progress && result.progress.length > 0) {
                setPipelineProgress(result.progress);
            }

            setPipelineStatus(result.status || 'completed');

            if (result.error) {
                showToast(`Error: ${result.error}`, 'error');
                setPipelineStatus('error');
            } else {
                const taskCount = result.task_count || 0;
                showToast(
                    result.status === 'completed'
                        ? `Pipeline complete! ${taskCount} tasks processed.`
                        : `Created ${taskCount} tasks from your request`,
                    'success'
                );
            }

            setRequestText('');
            refresh();
        } catch (err: any) {
            showToast(err.message, 'error');
            setPipelineStatus('error');
            setPipelineProgress(prev => [...prev, {
                stage: 'error',
                message: `Failed: ${err.message}`,
                timestamp: new Date().toISOString(),
            }]);
        } finally {
            setSubmitting(false);
        }
    }

    async function handleExecuteTask(taskId: number) {
        showToast(`Executing task #${taskId}...`, 'info');
        try {
            const result = await api.executeTask(taskId);
            const fileCount = result.files_produced || 0;
            showToast(
                `Task #${taskId} executed — ${fileCount} files produced, now in review`,
                'success'
            );
            refresh();
        } catch (err: any) {
            showToast(`Execution failed: ${err.message}`, 'error');
        }
    }

    async function handleReviewTask(taskId: number) {
        showToast(`Reviewing task #${taskId}...`, 'info');
        try {
            const result = await api.reviewTask(taskId);
            if (result.approved) {
                const fileCount = result.files_written?.length || 0;
                showToast(`Task #${taskId} approved — ${fileCount} files written to project`, 'success');
            } else {
                showToast(`Task #${taskId} needs revision — sent back for re-work`, 'info');
            }
            refresh();
        } catch (err: any) {
            showToast(`Review failed: ${err.message}`, 'error');
        }
    }

    function getStatValue(key: string): number {
        if (!stats) return 0;
        switch (key) {
            case 'total': return stats.total_tasks;
            case 'progress': return stats.task_counts?.in_progress || 0;
            case 'review': return stats.task_counts?.review || 0;
            case 'done': return stats.task_counts?.done || 0;
            case 'artifacts': return stats.total_artifacts;
            case 'llm': return stats.llm_telemetry?.total_calls || 0;
            case 'playbooks': return stats.ace_stats?.playbook_count || 0;
            default: return 0;
        }
    }

    function dismissProgress() {
        setPipelineProgress([]);
        setPipelineStatus('');
    }

    return (
        <div className="app-layout">
            {/* Header */}
            <header className="header">
                <div className="header-brand">
                    <span className="logo">🎼</span>
                    <h1>Orchestra AI</h1>
                    <span className="version">v1.0</span>
                </div>
                <div className="header-status">
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                        CodeLlama-7B
                    </span>
                    <div className="status-dot" />
                    <span style={{ fontSize: '12px', color: 'var(--green)', fontWeight: 500 }}>Connected</span>
                </div>
            </header>

            {/* Request Input */}
            <div className="request-form">
                <div className="request-input-group">
                    <input
                        className="request-input"
                        placeholder="Describe a feature, bug fix, or project to build…"
                        value={requestText}
                        onChange={(e) => setRequestText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSubmitRequest()}
                        disabled={submitting}
                    />
                    <input
                        className="request-input"
                        style={{ maxWidth: '140px', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}
                        placeholder="project"
                        value={projectName}
                        onChange={(e) => setProjectName(e.target.value)}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={handleSubmitRequest}
                        disabled={submitting || !requestText.trim()}
                    >
                        {submitting ? '⏳ Working…' : '🚀 Submit'}
                    </button>
                    <button className="btn btn-ghost" onClick={refresh} title="Refresh dashboard">
                        ↻
                    </button>
                </div>
            </div>

            {/* Pipeline Progress Panel */}
            {pipelineProgress.length > 0 && (
                <div className="pipeline-progress">
                    <div className="pipeline-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontSize: '14px' }}>
                                {STAGE_ICONS[pipelineStatus] || '⏳'}
                            </span>
                            <span style={{ fontSize: '12px', fontWeight: 600 }}>
                                Pipeline {pipelineStatus === 'completed' ? 'Complete' :
                                         pipelineStatus === 'error' ? 'Failed' : 'Running...'}
                            </span>
                            {submitting && (
                                <div className="spinner" style={{ width: '14px', height: '14px' }} />
                            )}
                        </div>
                        {!submitting && (
                            <button className="btn btn-ghost btn-sm" onClick={dismissProgress} style={{ fontSize: '10px' }}>
                                Dismiss
                            </button>
                        )}
                    </div>
                    <div className="pipeline-log">
                        {pipelineProgress.map((entry, i) => (
                            <div key={i} className={`pipeline-entry pipeline-${entry.stage}`}>
                                <span className="pipeline-icon">
                                    {STAGE_ICONS[entry.stage] || '•'}
                                </span>
                                <span className="pipeline-msg">{entry.message}</span>
                            </div>
                        ))}
                        <div ref={progressEndRef} />
                    </div>
                </div>
            )}

            {/* Stats */}
            {stats && (
                <div className="stats-bar">
                    {STAT_CARDS.map(card => (
                        <div key={card.key} className={`stat-card ${card.variant}`}>
                            <div className="stat-label">{card.label}</div>
                            <div className="stat-value">{getStatValue(card.key)}</div>
                        </div>
                    ))}
                </div>
            )}

            {/* Main Content */}
            <div className="main-content">
                <TaskBoard
                    onExecuteTask={handleExecuteTask}
                    onReviewTask={handleReviewTask}
                    refreshTrigger={refreshTrigger}
                />
                <div className="sidebar">
                    <AgentPanel refreshTrigger={refreshTrigger} />
                    <AgentFeed refreshTrigger={refreshTrigger} />
                    <ArtifactViewer refreshTrigger={refreshTrigger} />
                </div>
            </div>

            {/* Toast */}
            {toast && (
                <div className={`toast toast-${toast.type}`}>{toast.message}</div>
            )}
        </div>
    );
}
