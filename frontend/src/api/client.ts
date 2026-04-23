const BASE = '/api';

async function request(path: string, options?: RequestInit) {
    const res = await fetch(`${BASE}${path}`, {
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        ...options,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Request failed');
    }
    return res.json();
}

export const api = {
    // Dashboard
    getStats: () => request('/dashboard/stats'),
    getActivityFeed: (limit = 50) => request(`/dashboard/activity-feed?limit=${limit}`),

    // Tasks
    getTasks: (status?: string) => request(`/tasks${status ? `?status=${status}` : ''}`),
    getBoard: (project?: string) => request(`/tasks/board${project ? `?project=${project}` : ''}`),
    createTask: (data: any) => request('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
    updateTask: (id: number, data: any) => request(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deleteTask: (id: number) => request(`/tasks/${id}`, { method: 'DELETE' }),

    // Agents
    getAgents: () => request('/agents/'),
    updateAgent: (id: number, data: any) => request(`/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

    // Orchestrator
    submitRequest: (description: string, projectName = 'default') =>
        request('/orchestrator/request', {
            method: 'POST',
            body: JSON.stringify({ description, project_name: projectName }),
        }),
    executeTask: (taskId: number) =>
        request('/orchestrator/execute', { method: 'POST', body: JSON.stringify({ task_id: taskId }) }),
    reviewTask: (taskId: number) =>
        request('/orchestrator/review', { method: 'POST', body: JSON.stringify({ task_id: taskId }) }),
    getWorkflows: () => request('/orchestrator/workflows'),
    getWorkflowProgress: (workflowId: string) =>
        request(`/orchestrator/workflows/${workflowId}/progress`),

    // Artifacts — now supports filtering by task_id
    getArtifacts: (taskId?: number) =>
        request(`/artifacts/${taskId ? `?task_id=${taskId}` : ''}`),

    // Pull Requests
    getPRs: (status?: string) => request(`/pull-requests/${status ? `?status=${status}` : ''}`),
    approvePR: (id: number) => request(`/pull-requests/${id}/approve`, { method: 'POST' }),
    mergePR: (id: number) => request(`/pull-requests/${id}/merge`, { method: 'POST' }),
};
