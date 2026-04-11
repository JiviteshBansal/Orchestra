import { useState, useEffect } from 'react';
import { api } from '../api/client';

interface ActivityItem {
    id: number;
    action: string;
    agent_name: string;
    task_title: string;
    status: string;
    duration_ms: number | null;
    timestamp: string;
}

interface Props {
    refreshTrigger: number;
}

export default function AgentFeed({ refreshTrigger }: Props) {
    const [feed, setFeed] = useState<ActivityItem[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadFeed();
    }, [refreshTrigger]);

    async function loadFeed() {
        try {
            setLoading(true);
            const data = await api.getActivityFeed(20);
            setFeed(data);
        } catch (err) {
            console.error('Failed to load feed:', err);
        } finally {
            setLoading(false);
        }
    }

    function formatTime(ts: string) {
        if (!ts) return '';
        const d = new Date(ts);
        return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    function formatDuration(ms: number | null) {
        if (!ms) return '';
        if (ms < 1000) return `${Math.round(ms)}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
    }

    if (loading && feed.length === 0) {
        return (
            <div className="panel">
                <div className="panel-header"><h3>Activity</h3></div>
                <div className="loading"><div className="spinner" />Loading…</div>
            </div>
        );
    }

    return (
        <div className="panel">
            <div className="panel-header">
                <h3>Activity</h3>
                <button className="btn btn-ghost btn-sm" onClick={loadFeed} title="Refresh feed">↻</button>
            </div>
            {feed.length === 0 ? (
                <div className="empty-state">
                    <span className="empty-state-icon">📡</span>
                    No activity yet — submit a request to get started
                </div>
            ) : (
                feed.map(item => (
                    <div key={item.id} className="activity-item">
                        <div className={`activity-dot ${item.status}`} />
                        <div className="activity-content">
                            <div className="activity-agent">{item.agent_name}</div>
                            <div className="activity-action">
                                {item.action} — {item.task_title}
                                {item.duration_ms ? ` (${formatDuration(item.duration_ms)})` : ''}
                            </div>
                            <div className="activity-time">{formatTime(item.timestamp)}</div>
                        </div>
                    </div>
                ))
            )}
        </div>
    );
}
