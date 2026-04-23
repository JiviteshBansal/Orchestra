import { useState, useEffect } from 'react';
import { api } from '../api/client';

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
    refreshTrigger: number;
}

const TYPE_EMOJI: Record<string, string> = {
    code: '💻',
    document: '📄',
    design: '🎨',
    test: '🧪',
    config: '⚙️',
    review: '🔍',
    style: '🎨',
    sql: '🗄️',
};

const LANG_MAP: Record<string, string> = {
    py: 'Python', tsx: 'React', ts: 'TypeScript', js: 'JavaScript',
    css: 'CSS', html: 'HTML', sql: 'SQL', md: 'Markdown', json: 'JSON',
};

function getFileLang(name: string): string {
    const ext = name.split('.').pop()?.toLowerCase() || '';
    return LANG_MAP[ext] || ext.toUpperCase();
}

export default function ArtifactViewer({ refreshTrigger }: Props) {
    const [artifacts, setArtifacts] = useState<Artifact[]>([]);
    const [selected, setSelected] = useState<Artifact | null>(null);
    const [filter, setFilter] = useState<string>('all');

    useEffect(() => {
        loadArtifacts();
    }, [refreshTrigger]);

    async function loadArtifacts() {
        try {
            const data = await api.getArtifacts();
            setArtifacts(data);
        } catch (err) {
            console.error('Failed to load artifacts:', err);
        }
    }

    const filtered = filter === 'all'
        ? artifacts
        : filter === 'files'
            ? artifacts.filter(a => a.file_path)
            : artifacts.filter(a => a.artifact_type === filter);

    const fileCount = artifacts.filter(a => a.file_path).length;
    const reviewCount = artifacts.filter(a => a.artifact_type === 'review').length;

    return (
        <div className="panel">
            <div className="panel-header">
                <h3>Artifacts</h3>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {artifacts.length} total · {fileCount} files
                </span>
            </div>

            {/* Filter tabs */}
            <div style={{ display: 'flex', gap: '4px', marginBottom: '10px', flexWrap: 'wrap' }}>
                {[
                    { key: 'all', label: 'All' },
                    { key: 'files', label: `📂 Files (${fileCount})` },
                    { key: 'code', label: '💻 Code' },
                    { key: 'review', label: `🔍 Reviews (${reviewCount})` },
                ].map(tab => (
                    <button
                        key={tab.key}
                        className={`btn btn-sm ${filter === tab.key ? 'btn-primary' : 'btn-ghost'}`}
                        style={{ fontSize: '10px', padding: '3px 8px' }}
                        onClick={() => setFilter(tab.key)}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {selected ? (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)} style={{ fontSize: '11px' }}>←</button>
                            <span style={{ fontSize: '12px', fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                                {TYPE_EMOJI[selected.artifact_type] || '📎'} {selected.file_path || selected.title}
                            </span>
                        </div>
                        {selected.file_path && (
                            <span className="task-card-badge" style={{ fontSize: '9px', background: 'var(--bg-glass)', color: 'var(--text-muted)' }}>
                                {getFileLang(selected.file_path)}
                            </span>
                        )}
                    </div>
                    <pre className="code-viewer">{selected.content || 'No content'}</pre>
                </div>
            ) : (
                <div className="artifact-list">
                    {filtered.length === 0 ? (
                        <div className="empty-state">
                            <span className="empty-state-icon">📦</span>
                            {filter === 'all' ? 'No artifacts generated yet' : `No ${filter} artifacts`}
                        </div>
                    ) : (
                        filtered.map(art => (
                            <div key={art.id} className="artifact-item" onClick={() => setSelected(art)}>
                                <div className="artifact-title">
                                    {TYPE_EMOJI[art.artifact_type] || '📎'}{' '}
                                    {art.file_path || art.title}
                                </div>
                                <div className="artifact-meta">
                                    Task #{art.task_id} · {art.artifact_type}
                                    {art.file_path && ` · ${getFileLang(art.file_path)}`}
                                    {art.content && ` · ${art.content.length} chars`}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
