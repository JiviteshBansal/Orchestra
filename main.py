from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import requests
import os

app = Flask(__name__)
CORS(app)

DB_PATH = "data/database.db"
LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://host.docker.internal:1234/v1/chat/completions")
MODEL_NAME = "codellama-7b-instruct"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_database_snapshot():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    snapshot_lines = []

    for table in tables:
        table_name = table["name"]
        snapshot_lines.append(f"Table: {table_name}")

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [col["name"] for col in columns]
        snapshot_lines.append("Columns: " + ", ".join(column_names))

        cursor.execute(f"SELECT * FROM {table_name} LIMIT 50")
        rows = cursor.fetchall()

        if rows:
            snapshot_lines.append("Rows:")
            for row in rows:
                snapshot_lines.append(
                    " | ".join(str(row[col]) for col in column_names)
                )
        else:
            snapshot_lines.append("Rows: <empty>")

        snapshot_lines.append("")

    conn.close()
    return "\n".join(snapshot_lines)


def ask_llm(question, db_snapshot, system_instruction=None, tone=None):
    system_content = (
        "You are a database analyst. "
        "Answer only using the provided database snapshot. "
        "Do not invent tables, columns, or rows."
    )

    if system_instruction:
        system_content = system_instruction
    
    if tone:
        system_content += f" Answer in a {tone} tone."

    messages = [
        {
            "role": "system",
            "content": system_content
        },
        {
            "role": "user",
            "content": (
                f"Database snapshot:\n{db_snapshot}\n\n"
                f"Question:\n{question}"
            ) if db_snapshot else question
        }
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7 if tone else 0.2,
        "max_tokens": 512
    }

    response = requests.post(
        LM_STUDIO_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=120
    )

    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


@app.route("/", methods=["GET"])
def home():
    return "Orchestra backend running on port 3000"


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json()
    if not body or "message" not in body:
        return jsonify({"error": "Missing message"}), 400

    message = body["message"]
    tone = body.get("tone")
    training_data = body.get("training_data")

    answer = ask_llm(message, None, system_instruction=training_data, tone=tone)
    return jsonify({"answer": answer})


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    from flask import Response
    import json
    
    body = request.get_json()
    if not body or "message" not in body:
        return jsonify({"error": "Missing message"}), 400

    message = body["message"]
    tone = body.get("tone")
    training_data = body.get("training_data")

    def generate():
        system_content = "You are a helpful assistant."
        
        if training_data:
            system_content = training_data
        
        if tone:
            system_content += f" Answer in a {tone} tone."

        messages = [
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": message
            }
        ]

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.7 if tone else 0.2,
            "max_tokens": 512,
            "stream": True
        }

        try:
            response = requests.post(
                LM_STUDIO_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            data = json.loads(data_str)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')



@app.route("/api/model-status", methods=["GET"])
def model_status():
    try:
        base_url = os.environ.get("LM_STUDIO_URL", "http://host.docker.internal:1234/v1/chat/completions")
        status_url = base_url.replace("/chat/completions", "/models")
        r = requests.get(status_url, timeout=2)
        running = r.status_code == 200
    except Exception:
        running = False

    return jsonify({"running": running})


@app.route("/api/tables", methods=["GET"])
def get_tables():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    result = {}

    for table in tables:
        table_name = table["name"]

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col["name"] for col in cursor.fetchall()]

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        rows = [[row[col] for col in columns] for row in rows]

        result[table_name] = {
            "columns": columns,
            "rows": rows
        }

    conn.close()
    return jsonify({"tables": result})


@app.route("/ask-db", methods=["POST"])
def ask_db():
    body = request.get_json()

    if not body or "question" not in body:
        return jsonify({"error": "Missing question"}), 400

    question = body["question"]
    db_snapshot = get_database_snapshot()
    answer = ask_llm(question, db_snapshot)

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
