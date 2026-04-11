import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface Task {
    id: number;
    title: string;
    description: string;
    status: string;
    risk_level: string;
    effort_estimate: string;
    owner_agent_id: number | null;
    acceptance_criteria: string;
}

interface Board {
    backlog: Task[];
    in_progress: Task[];
    review: Task[];
    done: Task[];
}

interface Props {
    onExecuteTask: (taskId: number) => void;
    onReviewTask: (taskId: number) => void;
    refreshTrigger: number;
}

const COLUMN_CONFIG = [
    { key: 'backlog' as const, label: 'Backlog', className: 'backlog' },
    { key: 'in_progress' as const, label: 'In Progress', className: 'in-progress' },
    { key: 'review' as const, label: 'Review', className: 'review' },
    { key: 'done' as const, label: 'Done', className: 'done' },
];

const EMPTY_MESSAGES: Record<string, { icon: string; text: string }> = {
    backlog: { icon: '📥', text: 'No tasks in backlog' },
    in_progress: { icon: '⏳', text: 'Nothing in progress' },
    review: { icon: '🔎', text: 'Nothing to review' },
    done: { icon: '✓', text: 'No completed tasks yet' },
};

export default function TaskBoard({ onExecuteTask, onReviewTask, refreshTrigger }: Props) {
    const [board, setBoard] = useState<Board>({ backlog: [], in_progress: [], review: [], done: [] });
    const [loading, setLoading] = useState(true);
    const [selectedTask, setSelectedTask] = useState<Task | null>(null);

    useEffect(() => {
        loadBoard();
    }, [refreshTrigger]);

    async function loadBoard() {
        try {
            setLoading(true);
            const data = await api.getBoard();
            setBoard(data);
        } catch (err) {
            console.error('Failed to load board:', err);
        } finally {
            setLoading(false);
        }
    }

    if (loading) {
        return <div className="loading"><div className="spinner" />Loading tasks…</div>;
    }

    return (
        <div>
            <div className="kanban-board">
                {COLUMN_CONFIG.map(col => (
                    <div key={col.key} className={`kanban-column ${col.className}`}>
                        <div className="kanban-column-header">
                            <h3>{col.label}</h3>
                            <span className="kanban-count">{board[col.key].length}</span>
                        </div>
                        {board[col.key].map(task => (
                            <div key={task.id} className="task-card" onClick={() => setSelectedTask(task)}>
                                <div className="task-card-title">{task.title}</div>
                                <div className="task-card-desc">{task.description}</div>
                                <div className="task-card-footer">
                                    <span className={`task-card-badge badge-risk-${task.risk_level}`}>
                                        {task.risk_level}
                                    </span>
                                    <span className="task-card-agent">#{task.id}</span>
                                </div>
                                <div className="task-card-actions">
                                    {col.key === 'backlog' && (
                                        <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); onExecuteTask(task.id); }}>
                                            Execute
                                        </button>
                                    )}
                                    {col.key === 'in_progress' && (
                                        <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); onExecuteTask(task.id); }}>
                                            Execute
                                        </button>
                                    )}
                                    {col.key === 'review' && (
                                        <button className="btn btn-warning btn-sm" onClick={(e) => { e.stopPropagation(); onReviewTask(task.id); }}>
                                            Review
                                        </button>
                                    )}
                                    {col.key === 'done' && (
                                        <span className="task-card-badge badge-risk-low">Complete</span>
                                    )}
                                </div>
                            </div>
                        ))}
                        {board[col.key].length === 0 && (
                            <div className="empty-state">
                                <span className="empty-state-icon">{EMPTY_MESSAGES[col.key].icon}</span>
                                {EMPTY_MESSAGES[col.key].text}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {selectedTask && (
                <div className="modal-overlay" onClick={() => setSelectedTask(null)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <h2>{selectedTask.title}</h2>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '14px', fontSize: '13px', lineHeight: 1.6 }}>
                            {selectedTask.description}
                        </p>
                        {selectedTask.acceptance_criteria && (
                            <div style={{ marginBottom: '14px' }}>
                                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '4px' }}>
                                    Acceptance Criteria
                                </div>
                                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                                    {selectedTask.acceptance_criteria}
                                </p>
                            </div>
                        )}
                        <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', flexWrap: 'wrap' }}>
                            <span className={`task-card-badge badge-risk-${selectedTask.risk_level}`}>{selectedTask.risk_level}</span>
                            <span className="task-card-badge" style={{ background: 'var(--bg-glass)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
                                {selectedTask.effort_estimate}
                            </span>
                            <span className="task-card-badge" style={{ background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--accent-glow)' }}>
                                {selectedTask.status}
                            </span>
                        </div>
                        <div className="modal-actions">
                            <button className="btn btn-ghost" onClick={() => setSelectedTask(null)}>Close</button>
                            {selectedTask.status === 'backlog' && (
                                <button className="btn btn-primary" onClick={() => { onExecuteTask(selectedTask.id); setSelectedTask(null); }}>
                                    Execute Task
                                </button>
                            )}
                            {selectedTask.status === 'review' && (
                                <button className="btn btn-warning" onClick={() => { onReviewTask(selectedTask.id); setSelectedTask(null); }}>
                                    Review Task
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
