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

interface Artifact {
    id: number;
    task_id: number;
    agent_id: number;
    artifact_type: string;
    title: string;
    content: string;
    file_path: string | null;
    created_at: string;
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

const LANG_MAP: Record<string, string> = {
    py: 'Python', python: 'Python',
    tsx: 'React TSX', jsx: 'React JSX',
    ts: 'TypeScript', js: 'JavaScript',
    css: 'CSS', html: 'HTML',
    sql: 'SQL', md: 'Markdown',
    json: 'JSON', yaml: 'YAML',
};

function getFileExt(name: string): string {
    return name.split('.').pop()?.toLowerCase() || '';
}

function getFileLang(name: string): string {
    const ext = getFileExt(name);
    return LANG_MAP[ext] || ext.toUpperCase();
}

export default function TaskBoard({ onExecuteTask, onReviewTask, refreshTrigger }: Props) {
    const [board, setBoard] = useState<Board>({ backlog: [], in_progress: [], review: [], done: [] });
    const [loading, setLoading] = useState(true);
    const [selectedTask, setSelectedTask] = useState<Task | null>(null);
    const [taskArtifacts, setTaskArtifacts] = useState<Artifact[]>([]);
    const [viewingArtifact, setViewingArtifact] = useState<Artifact | null>(null);
    const [loadingArtifacts, setLoadingArtifacts] = useState(false);

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

    async function openTaskDetail(task: Task) {
        setSelectedTask(task);
        setViewingArtifact(null);
        setLoadingArtifacts(true);
        try {
            const arts = await api.getArtifacts(task.id);
            setTaskArtifacts(arts);
        } catch (err) {
            console.error('Failed to load task artifacts:', err);
            setTaskArtifacts([]);
        } finally {
            setLoadingArtifacts(false);
        }
    }

    function closeModal() {
        setSelectedTask(null);
        setTaskArtifacts([]);
        setViewingArtifact(null);
    }

    if (loading) {
        return <div className="loading"><div className="spinner" />Loading tasks…</div>;
    }

    const fileArtifacts = taskArtifacts.filter(a => a.file_path && a.artifact_type !== 'review');
    const reviewArtifacts = taskArtifacts.filter(a => a.artifact_type === 'review');
    const mainArtifacts = taskArtifacts.filter(a => !a.file_path && a.artifact_type !== 'review');

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
                            <div key={task.id} className="task-card" onClick={() => openTaskDetail(task)}>
                                <div className="task-card-title">{task.title}</div>
                                <div className="task-card-desc">{task.description?.substring(0, 100)}</div>
                                <div className="task-card-footer">
                                    <span className={`task-card-badge badge-risk-${task.risk_level}`}>
                                        {task.risk_level}
                                    </span>
                                    <span className="task-card-agent">#{task.id}</span>
                                </div>
                                <div className="task-card-actions">
                                    {col.key === 'backlog' && (
                                        <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); onExecuteTask(task.id); }}>
                                            ▶ Execute
                                        </button>
                                    )}
                                    {col.key === 'in_progress' && (
                                        <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); onExecuteTask(task.id); }}>
                                            ▶ Execute
                                        </button>
                                    )}
                                    {col.key === 'review' && (
                                        <button className="btn btn-warning btn-sm" onClick={(e) => { e.stopPropagation(); onReviewTask(task.id); }}>
                                            🔍 Review
                                        </button>
                                    )}
                                    {col.key === 'done' && (
                                        <button className="btn btn-sm" style={{ background: 'var(--green)', color: '#000', fontWeight: 600 }}
                                                onClick={(e) => { e.stopPropagation(); openTaskDetail(task); }}>
                                            📂 View Code
                                        </button>
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

            {/* Task Detail Modal */}
            {selectedTask && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal modal-wide" onClick={(e) => e.stopPropagation()}>

                        {/* Header */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                            <div>
                                <h2 style={{ margin: 0, fontSize: '18px' }}>{selectedTask.title}</h2>
                                <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px' }}>
                                    Task #{selectedTask.id}
                                </p>
                            </div>
                            <button className="btn btn-ghost btn-sm" onClick={closeModal}>✕</button>
                        </div>

                        {/* Description */}
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '14px', fontSize: '13px', lineHeight: 1.6 }}>
                            {selectedTask.description}
                        </p>

                        {/* Acceptance Criteria */}
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

                        {/* Badges */}
                        <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', flexWrap: 'wrap' }}>
                            <span className={`task-card-badge badge-risk-${selectedTask.risk_level}`}>{selectedTask.risk_level}</span>
                            <span className="task-card-badge" style={{ background: 'var(--bg-glass)', color: 'var(--text-secondary)', border: '1px solid var(--border-subtle)' }}>
                                {selectedTask.effort_estimate}
                            </span>
                            <span className="task-card-badge" style={{ background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--accent-glow)' }}>
                                {selectedTask.status}
                            </span>
                        </div>

                        {/* Artifacts Section */}
                        {loadingArtifacts ? (
                            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                                <div className="spinner" style={{ margin: '0 auto 8px' }} />
                                Loading artifacts...
                            </div>
                        ) : viewingArtifact ? (
                            /* Artifact Code Viewer */
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                        <button className="btn btn-ghost btn-sm" onClick={() => setViewingArtifact(null)}>← Back</button>
                                        <span style={{ fontSize: '13px', fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                                            {viewingArtifact.file_path || viewingArtifact.title}
                                        </span>
                                        <span className="task-card-badge" style={{ fontSize: '10px', background: 'var(--bg-glass)', color: 'var(--text-muted)' }}>
                                            {getFileLang(viewingArtifact.file_path || viewingArtifact.title)}
                                        </span>
                                    </div>
                                </div>
                                <pre className="code-viewer">{viewingArtifact.content}</pre>
                            </div>
                        ) : (
                            /* File List */
                            <>
                                {fileArtifacts.length > 0 && (
                                    <div style={{ marginBottom: '14px' }}>
                                        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--green)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                                            📂 Generated Files ({fileArtifacts.length})
                                        </div>
                                        <div className="file-list">
                                            {fileArtifacts.map(art => (
                                                <div key={art.id} className="file-item" onClick={() => setViewingArtifact(art)}>
                                                    <span className="file-icon">
                                                        {art.artifact_type === 'code' ? '💻' :
                                                         art.artifact_type === 'style' ? '🎨' :
                                                         art.artifact_type === 'config' ? '⚙️' :
                                                         art.artifact_type === 'sql' ? '🗄️' : '📄'}
                                                    </span>
                                                    <span className="file-name">{art.file_path || art.title}</span>
                                                    <span className="file-lang">{getFileLang(art.file_path || art.title)}</span>
                                                    <span className="file-size">{art.content?.length || 0} chars</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {mainArtifacts.length > 0 && fileArtifacts.length === 0 && (
                                    <div style={{ marginBottom: '14px' }}>
                                        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                                            📋 Agent Output
                                        </div>
                                        {mainArtifacts.map(art => (
                                            <div key={art.id} className="file-item" onClick={() => setViewingArtifact(art)} style={{ cursor: 'pointer' }}>
                                                <span className="file-icon">💻</span>
                                                <span className="file-name">{art.title}</span>
                                                <span className="file-size">{art.content?.length || 0} chars</span>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {reviewArtifacts.length > 0 && (
                                    <div style={{ marginBottom: '14px' }}>
                                        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--yellow)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                                            🔍 Reviews ({reviewArtifacts.length})
                                        </div>
                                        {reviewArtifacts.map(art => {
                                            let review: any = {};
                                            try { review = JSON.parse(art.content); } catch {}
                                            return (
                                                <div key={art.id} className="review-card">
                                                    <div style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}>
                                                        <span className={`task-card-badge ${review.approved ? 'badge-risk-low' : 'badge-risk-high'}`}>
                                                            {review.approved ? '✓ Approved' : '↻ Revision Needed'}
                                                        </span>
                                                    </div>
                                                    {review.comments && (
                                                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, marginTop: '6px' }}>
                                                            {review.comments.substring(0, 500)}
                                                        </p>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}

                                {taskArtifacts.length === 0 && (
                                    <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                                        No artifacts generated yet. Execute this task to produce code.
                                    </div>
                                )}
                            </>
                        )}

                        {/* Actions */}
                        <div className="modal-actions" style={{ marginTop: '16px' }}>
                            <button className="btn btn-ghost" onClick={closeModal}>Close</button>
                            {selectedTask.status === 'backlog' && (
                                <button className="btn btn-primary" onClick={() => { onExecuteTask(selectedTask.id); closeModal(); }}>
                                    ▶ Execute Task
                                </button>
                            )}
                            {selectedTask.status === 'in_progress' && (
                                <button className="btn btn-primary" onClick={() => { onExecuteTask(selectedTask.id); closeModal(); }}>
                                    ▶ Continue Execution
                                </button>
                            )}
                            {selectedTask.status === 'review' && (
                                <button className="btn btn-warning" onClick={() => { onReviewTask(selectedTask.id); closeModal(); }}>
                                    🔍 Review & Approve
                                </button>
                            )}
                            {selectedTask.status === 'done' && fileArtifacts.length > 0 && (
                                <button className="btn btn-primary" onClick={() => setViewingArtifact(fileArtifacts[0])}>
                                    📂 View Code
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
