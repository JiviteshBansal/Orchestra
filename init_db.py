import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")

os.makedirs(DATA_DIR, exist_ok=True)

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    model TEXT,
    status TEXT DEFAULT 'active',
    last_active TIMESTAMP,
    tasks_completed INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    acceptance_criteria TEXT,
    status TEXT NOT NULL,
    owner_agent TEXT,
    risk_level TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (owner_agent) REFERENCES agents(id)
)
""")

cursor.execute("""
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
)
""")

cursor.execute("""
CREATE TABLE run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    agent_id TEXT,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id),
    FOREIGN KEY (agent_id) REFERENCES agents(id)
)
""")

conn.commit()
conn.close()

print("Database recreated successfully.")
