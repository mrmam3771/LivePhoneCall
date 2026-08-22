"""Local-only SQLite API for the Vue voice chat workspace."""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = ROOT_DIR / "chat-data.sqlite3"
DEFAULT_AGENT_ID = "qwen-general"
DEFAULT_AGENT = {
    "id": DEFAULT_AGENT_ID,
    "name": "Qwen General",
    "description": "Balanced bilingual voice assistant",
    "system_prompt": "You are a concise and helpful bilingual voice assistant.",
    "provider": "deepseek",
    "base_url": "",
    "request_path": "/chat/completions",
    "api_key": "",
    "model": "deepseek-chat",
    "language": "Auto",
    "voice": "Vivian",
    "built_in": True,
    "created_at": 0,
    "updated_at": 0,
}


def now_ms() -> int:
    return int(time.time() * 1000)


def as_json(value):
    return jsonify(value)


def row_to_agent(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "description": row["description"],
        "systemPrompt": row["system_prompt"], "provider": row["provider"], "baseUrl": row["base_url"],
        "requestPath": row["request_path"], "apiKey": row["api_key"], "model": row["model"], "language": row["language"], "voice": row["voice"],
        "builtIn": bool(row["built_in"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def row_to_session(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "agentId": row["agent_id"], "title": row["title"], "preview": row["preview"],
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def row_to_message(row: sqlite3.Row) -> dict:
    item = {
        "id": row["id"], "sessionId": row["session_id"], "role": row["role"], "type": row["type"],
        "content": row["content"], "mimeType": row["mime_type"], "duration": row["duration"],
        "createdAt": row["created_at"],
    }
    return item


def create_app(database_path: Path | str = DEFAULT_DATABASE_PATH, testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.update(DATABASE_PATH=str(database_path), TESTING=testing)
    initialise_database(app.config["DATABASE_PATH"])

    def connection() -> sqlite3.Connection:
        conn = sqlite3.connect(app.config["DATABASE_PATH"])
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def payload() -> dict:
        return request.get_json(silent=False) or {}

    def require_session(conn: sqlite3.Connection, session_id: str) -> sqlite3.Row:
        session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            raise LookupError("Conversation not found")
        return session

    @app.errorhandler(LookupError)
    def not_found(error):
        return as_json({"error": str(error)}), 404

    @app.errorhandler(ValueError)
    def invalid_request(error):
        return as_json({"error": str(error)}), 400

    @app.get("/api/chat/health")
    def health():
        return as_json({"ready": True, "database": Path(app.config["DATABASE_PATH"]).name})

    @app.get("/api/chat/bootstrap")
    def bootstrap():
        with connection() as conn:
            agents = [row_to_agent(row) for row in conn.execute("SELECT * FROM agents ORDER BY built_in DESC, updated_at DESC")]
            sessions = [row_to_session(row) for row in conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")]
        return as_json({"agents": agents, "sessions": sessions})

    @app.get("/api/chat/agents")
    def list_agents():
        with connection() as conn:
            return as_json([row_to_agent(row) for row in conn.execute("SELECT * FROM agents ORDER BY built_in DESC, updated_at DESC")])

    @app.post("/api/chat/agents")
    def create_agent():
        data = payload()
        name = str(data.get("name", "")).strip()
        if not name:
            raise ValueError("Agent name is required")
        identifier, timestamp = str(uuid.uuid4()), now_ms()
        agent = normalise_agent(data, identifier, False, timestamp)
        with connection() as conn:
            conn.execute("""INSERT INTO agents (id, name, description, system_prompt, provider, base_url, request_path, api_key, model, language, voice, built_in, created_at, updated_at)
                VALUES (:id, :name, :description, :system_prompt, :provider, :base_url, :request_path, :api_key, :model, :language, :voice, :built_in, :created_at, :updated_at)""", agent)
        return as_json(fetch_agent(app.config["DATABASE_PATH"], identifier)), 201

    @app.put("/api/chat/agents/<agent_id>")
    def update_agent(agent_id: str):
        data = payload()
        with connection() as conn:
            existing = conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
            if not existing:
                raise LookupError("Agent not found")
            merged = {**row_to_agent(existing), **data, "id": agent_id}
            agent = normalise_agent(merged, agent_id, bool(existing["built_in"]), existing["created_at"])
            conn.execute("""UPDATE agents SET name=:name, description=:description, system_prompt=:system_prompt, provider=:provider,
                base_url=:base_url, request_path=:request_path, api_key=:api_key, model=:model, language=:language, voice=:voice, updated_at=:updated_at WHERE id=:id""", agent)
        return as_json(fetch_agent(app.config["DATABASE_PATH"], agent_id))

    @app.delete("/api/chat/agents/<agent_id>")
    def delete_agent(agent_id: str):
        if agent_id == DEFAULT_AGENT_ID:
            raise ValueError("The built-in Agent cannot be deleted")
        with connection() as conn:
            if not conn.execute("SELECT 1 FROM agents WHERE id = ?", (agent_id,)).fetchone():
                raise LookupError("Agent not found")
            conn.execute("UPDATE sessions SET agent_id = ? WHERE agent_id = ?", (DEFAULT_AGENT_ID, agent_id))
            conn.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        return "", 204

    @app.get("/api/chat/sessions")
    def list_sessions():
        with connection() as conn:
            return as_json([row_to_session(row) for row in conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")])

    @app.post("/api/chat/sessions")
    def create_session():
        data = payload()
        agent_id = data.get("agentId", data.get("agent_id", DEFAULT_AGENT_ID))
        timestamp, identifier = now_ms(), str(uuid.uuid4())
        with connection() as conn:
            if not conn.execute("SELECT 1 FROM agents WHERE id = ?", (agent_id,)).fetchone():
                raise ValueError("Selected Agent does not exist")
            conn.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?)", (identifier, agent_id, "New conversation / 新会话", "No messages yet / 暂无消息", timestamp, timestamp))
        return as_json(fetch_session(app.config["DATABASE_PATH"], identifier)), 201

    @app.patch("/api/chat/sessions/<session_id>")
    def update_session(session_id: str):
        data = payload()
        agent_id = data.get("agentId", data.get("agent_id"))
        if not agent_id:
            raise ValueError("agentId is required")
        with connection() as conn:
            require_session(conn, session_id)
            if not conn.execute("SELECT 1 FROM agents WHERE id = ?", (agent_id,)).fetchone():
                raise ValueError("Selected Agent does not exist")
            conn.execute("UPDATE sessions SET agent_id = ?, updated_at = ? WHERE id = ?", (agent_id, now_ms(), session_id))
        return as_json(fetch_session(app.config["DATABASE_PATH"], session_id))

    @app.delete("/api/chat/sessions/<session_id>")
    def delete_session(session_id: str):
        with connection() as conn:
            require_session(conn, session_id)
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return "", 204

    @app.get("/api/chat/sessions/<session_id>/messages")
    def list_messages(session_id: str):
        with connection() as conn:
            require_session(conn, session_id)
            rows = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY created_at", (session_id,))
            return as_json([row_to_message(row) for row in rows])

    @app.post("/api/chat/sessions/<session_id>/messages")
    def add_message(session_id: str):
        data = payload()
        with connection() as conn:
            session = require_session(conn, session_id)
            message = insert_message(conn, session, data)
        return as_json(message), 201

    return app


def initialise_database(database_path: str | Path) -> None:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
              id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', system_prompt TEXT NOT NULL DEFAULT '',
              provider TEXT NOT NULL DEFAULT 'custom', base_url TEXT NOT NULL DEFAULT '', request_path TEXT NOT NULL DEFAULT '/chat/completions', api_key TEXT NOT NULL DEFAULT '', model TEXT NOT NULL DEFAULT '',
              language TEXT NOT NULL DEFAULT 'Auto', voice TEXT NOT NULL DEFAULT 'Vivian', built_in INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
              id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), title TEXT NOT NULL, preview TEXT NOT NULL,
              created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, role TEXT NOT NULL,
              type TEXT NOT NULL, content TEXT NOT NULL, audio BLOB, mime_type TEXT, duration REAL, created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS messages_session_created ON messages(session_id, created_at);
            CREATE INDEX IF NOT EXISTS sessions_updated ON sessions(updated_at DESC);
        """)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(agents)")}
        if "request_path" not in columns:
            conn.execute("ALTER TABLE agents ADD COLUMN request_path TEXT NOT NULL DEFAULT '/chat/completions'")
        if "api_key" not in columns:
            conn.execute("ALTER TABLE agents ADD COLUMN api_key TEXT NOT NULL DEFAULT ''")
        conn.execute("""INSERT OR IGNORE INTO agents (id, name, description, system_prompt, provider, base_url, request_path, api_key, model,
            language, voice, built_in, created_at, updated_at) VALUES (:id, :name, :description, :system_prompt, :provider, :base_url,
            :request_path, :api_key, :model, :language, :voice, :built_in, :created_at, :updated_at)""", DEFAULT_AGENT)


def normalise_agent(data: dict, identifier: str, built_in: bool, created_at: int) -> dict:
    timestamp = now_ms()
    return {
        "id": identifier, "name": str(data.get("name", "")).strip(), "description": str(data.get("description", "")),
        "system_prompt": str(data.get("systemPrompt", data.get("system_prompt", ""))),
        "provider": str(data.get("provider", "custom")), "base_url": str(data.get("baseUrl", data.get("base_url", ""))),
        "request_path": str(data.get("requestPath", data.get("request_path", "/chat/completions"))) or "/chat/completions",
        "api_key": str(data.get("apiKey", data.get("api_key", ""))),
        "model": str(data.get("model", "")), "language": str(data.get("language", "Auto")), "voice": str(data.get("voice", "Vivian")),
        "built_in": int(built_in), "created_at": created_at, "updated_at": timestamp,
    }


def fetch_agent(database_path: str, agent_id: str) -> dict:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        return row_to_agent(conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone())


def fetch_session(database_path: str, session_id: str) -> dict:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        return row_to_session(conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone())


def insert_message(conn: sqlite3.Connection, session: sqlite3.Row, data: dict) -> dict:
    message_type = str(data.get("type", "text"))
    if message_type == "audio":
        raise ValueError("Audio recordings are not stored in live call mode")
    content = str(data.get("content", ""))
    if not content and message_type != "audio":
        raise ValueError("Message content is required")
    timestamp, identifier = now_ms(), str(uuid.uuid4())
    conn.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
        identifier, session["id"], str(data.get("role", "user")), message_type, content, None,
        None, None, timestamp,
    ))
    summary = " ".join(content.split())
    title = session["title"]
    if session["title"] == "New conversation / 新会话":
        title = summary[:34]
    conn.execute("UPDATE sessions SET title = ?, preview = ?, updated_at = ? WHERE id = ?", (title, summary[:62], timestamp, session["id"]))
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (identifier,)).fetchone()
    return row_to_message(row)


def format_duration(seconds: float | int | None) -> str:
    value = max(0, round(float(seconds or 0)))
    return f"{value // 60:02d}:{value % 60:02d}"


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8002, debug=False)
