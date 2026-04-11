import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface Artifact {
    id: number;
    task_id: number;
    agent_id: number;
    artifact_type: string;
    title: string;
    content: string;
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
};

export default function ArtifactViewer({ refreshTrigger }: Props) {
    const [artifacts, setArtifacts] = useState<Artifact[]>([]);
    const [selected, setSelected] = useState<Artifact | null>(null);

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

    return (
        <div className="panel">
            <div className="panel-header">
                <h3>Artifacts</h3>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {artifacts.length} total
                </span>
            </div>
            {selected ? (
                <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                        <span style={{ fontSize: '12.5px', fontWeight: 600 }}>
                            {TYPE_EMOJI[selected.artifact_type] || '📎'} {selected.title}
                        </span>
                        <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✕</button>
                    </div>
                    <div className="artifact-content">{selected.content || 'No content'}</div>
                </div>
            ) : (
                <div className="artifact-list">
                    {artifacts.length === 0 ? (
                        <div className="empty-state">
                            <span className="empty-state-icon">📦</span>
                            No artifacts generated yet
                        </div>
                    ) : (
                        artifacts.map(art => (
                            <div key={art.id} className="artifact-item" onClick={() => setSelected(art)}>
                                <div className="artifact-title">
                                    {TYPE_EMOJI[art.artifact_type] || '📎'} {art.title}
                                </div>
                                <div className="artifact-meta">
                                    Task #{art.task_id} · {art.artifact_type}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
