"""Local-only SQLite API for the Vue voice chat workspace."""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from pathlib import Path

from flask import Flask, jsonify, request


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = Path(os.getenv("CHAT_DATABASE_PATH", ROOT_DIR / "chat-data.sqlite3"))
DEFAULT_AGENT_ID = "qwen-general"
DEFAULT_MODEL_ID = "deepseek-chat"
DEFAULT_PROVIDER_ID = "deepseek"
DEFAULT_AGENT = {
    "id": DEFAULT_AGENT_ID,
    "name": "Qwen General",
    "description": "Balanced bilingual voice assistant",
    "system_prompt": "",
    "provider": "deepseek",
    "base_url": "",
    "request_path": "/chat/completions",
    "api_key": "",
    "model": "deepseek-chat",
    "language": "Auto",
    "voice": "Auto",
    "built_in": True,
    "created_at": 0,
    "updated_at": 0,
}
DEFAULT_MODEL = {"id": DEFAULT_MODEL_ID, "name": "DeepSeek Chat", "provider": "deepseek", "base_url": "https://api.deepseek.com/v1", "request_path": "/chat/completions", "api_key": "", "model": "deepseek-chat", "built_in": True, "created_at": 0, "updated_at": 0}
DEFAULT_PROVIDER = {"id": DEFAULT_PROVIDER_ID, "name": "DeepSeek", "api": "openai-completions", "base_url": "https://api.deepseek.com/v1", "api_key": "", "built_in": True, "created_at": 0, "updated_at": 0}


def now_ms() -> int:
    return int(time.time() * 1000)


def as_json(value):
    return jsonify(value)


def row_to_agent(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "name": row["name"], "description": row["description"],
        "systemPrompt": row["system_prompt"], "language": row["language"], "voice": row["voice"],
        "builtIn": bool(row["built_in"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def row_to_session(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"], "agentId": row["agent_id"], "modelId": row["model_id"], "title": row["title"], "preview": row["preview"],
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def row_to_message(row: sqlite3.Row) -> dict:
    item = {
        "id": row["id"], "sessionId": row["session_id"], "role": row["role"], "type": row["type"],
        "content": row["content"], "mimeType": row["mime_type"], "duration": row["duration"],
        "createdAt": row["created_at"],
    }
    return item


def row_to_model(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "providerId": row["provider_id"], "name": row["name"], "provider": row["provider"], "baseUrl": row["base_url"], "requestPath": row["request_path"], "apiKey": row["api_key"], "model": row["model"], "builtIn": bool(row["built_in"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

def row_to_provider(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "api": row["api"], "baseUrl": row["base_url"], "apiKey": row["api_key"], "builtIn": bool(row["built_in"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


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
            providers = [row_to_provider(row) for row in conn.execute("SELECT * FROM providers ORDER BY built_in DESC, updated_at DESC")]
            models = [row_to_model(row) for row in conn.execute("SELECT * FROM models ORDER BY built_in DESC, updated_at DESC")]
            sessions = [row_to_session(row) for row in conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")]
        return as_json({"agents": agents, "providers": providers, "models": models, "sessions": sessions})

    @app.get("/api/chat/providers")
    def list_providers():
        with connection() as conn:
            return as_json([row_to_provider(row) for row in conn.execute("SELECT * FROM providers ORDER BY built_in DESC, updated_at DESC")])

    @app.post("/api/chat/providers")
    def create_provider():
        data, identifier, timestamp = payload(), str(uuid.uuid4()), now_ms()
        if not str(data.get("name", "")).strip():
            raise ValueError("Provider name is required")
        provider = normalise_provider(data, identifier, False, timestamp)
        with connection() as conn:
            conn.execute("INSERT INTO providers VALUES (:id,:name,:api,:base_url,:api_key,:built_in,:created_at,:updated_at)", provider)
        return as_json(fetch_provider(app.config["DATABASE_PATH"], identifier)), 201

    @app.put("/api/chat/providers/<provider_id>")
    def update_provider(provider_id: str):
        data = payload()
        with connection() as conn:
            existing = conn.execute("SELECT * FROM providers WHERE id=?", (provider_id,)).fetchone()
            if not existing:
                raise LookupError("Provider not found")
            provider = normalise_provider({**row_to_provider(existing), **data}, provider_id, bool(existing["built_in"]), existing["created_at"])
            conn.execute("UPDATE providers SET name=:name,api=:api,base_url=:base_url,api_key=:api_key,updated_at=:updated_at WHERE id=:id", provider)
        return as_json(fetch_provider(app.config["DATABASE_PATH"], provider_id))

    @app.delete("/api/chat/providers/<provider_id>")
    def delete_provider(provider_id: str):
        if provider_id == DEFAULT_PROVIDER_ID:
            raise ValueError("The built-in provider cannot be deleted")
        with connection() as conn:
            if not conn.execute("SELECT 1 FROM providers WHERE id=?", (provider_id,)).fetchone():
                raise LookupError("Provider not found")
            if conn.execute("SELECT 1 FROM models WHERE provider_id=?", (provider_id,)).fetchone():
                raise ValueError("Delete or move this provider's models first")
            conn.execute("DELETE FROM providers WHERE id=?", (provider_id,))
        return "", 204

    @app.get("/api/chat/models")
    def list_models():
        with connection() as conn:
            return as_json([row_to_model(row) for row in conn.execute("SELECT * FROM models ORDER BY built_in DESC, updated_at DESC")])

    @app.post("/api/chat/models")
    def create_model():
        data, identifier, timestamp = payload(), str(uuid.uuid4()), now_ms()
        if not str(data.get("name", "")).strip() or not str(data.get("model", "")).strip(): raise ValueError("Model name and model identifier are required")
        model = normalise_model(data, identifier, False, timestamp)
        with connection() as conn:
            if not conn.execute("SELECT 1 FROM providers WHERE id=?", (model["provider_id"],)).fetchone():
                raise ValueError("Selected provider does not exist")
            conn.execute("INSERT INTO models (id,name,provider_id,provider,base_url,request_path,api_key,model,built_in,created_at,updated_at) VALUES (:id,:name,:provider_id,:provider,:base_url,:request_path,:api_key,:model,:built_in,:created_at,:updated_at)", model)
        return as_json(fetch_model(app.config["DATABASE_PATH"], identifier)), 201

    @app.put("/api/chat/models/<model_id>")
    def update_model(model_id: str):
        data = payload()
        with connection() as conn:
            existing = conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone()
            if not existing: raise LookupError("Model profile not found")
            model = normalise_model({**row_to_model(existing), **data}, model_id, bool(existing["built_in"]), existing["created_at"])
            if not conn.execute("SELECT 1 FROM providers WHERE id=?", (model["provider_id"],)).fetchone():
                raise ValueError("Selected provider does not exist")
            conn.execute("UPDATE models SET name=:name,provider_id=:provider_id,provider=:provider,base_url=:base_url,request_path=:request_path,api_key=:api_key,model=:model,updated_at=:updated_at WHERE id=:id", model)
        return as_json(fetch_model(app.config["DATABASE_PATH"], model_id))

    @app.delete("/api/chat/models/<model_id>")
    def delete_model(model_id: str):
        if model_id == DEFAULT_MODEL_ID: raise ValueError("The built-in model cannot be deleted")
        with connection() as conn:
            if not conn.execute("SELECT 1 FROM models WHERE id=?", (model_id,)).fetchone(): raise LookupError("Model profile not found")
            conn.execute("UPDATE sessions SET model_id=? WHERE model_id=?", (DEFAULT_MODEL_ID, model_id)); conn.execute("DELETE FROM models WHERE id=?", (model_id,))
        return "", 204

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
            model_id = data.get("modelId", data.get("model_id", DEFAULT_MODEL_ID))
            if not conn.execute("SELECT 1 FROM models WHERE id=?", (model_id,)).fetchone(): raise ValueError("Selected model does not exist")
            conn.execute("""INSERT INTO sessions (id,agent_id,model_id,title,preview,created_at,updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""", (identifier, agent_id, model_id, "New conversation / 新会话", "No messages yet / 暂无消息", timestamp, timestamp))
        return as_json(fetch_session(app.config["DATABASE_PATH"], identifier)), 201

    @app.patch("/api/chat/sessions/<session_id>")
    def update_session(session_id: str):
        data = payload()
        agent_id = data.get("agentId", data.get("agent_id")); model_id = data.get("modelId", data.get("model_id"))
        if not agent_id and not model_id: raise ValueError("agentId or modelId is required")
        with connection() as conn:
            require_session(conn, session_id)
            if agent_id and not conn.execute("SELECT 1 FROM agents WHERE id = ?", (agent_id,)).fetchone():
                raise ValueError("Selected Agent does not exist")
            if model_id and not conn.execute("SELECT 1 FROM models WHERE id=?", (model_id,)).fetchone(): raise ValueError("Selected model does not exist")
            conn.execute("UPDATE sessions SET agent_id = ?, model_id = ?, updated_at = ? WHERE id = ?", (agent_id or require_session(conn, session_id)["agent_id"], model_id or require_session(conn, session_id)["model_id"], now_ms(), session_id))
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
        conn.row_factory = sqlite3.Row
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
              id TEXT PRIMARY KEY, agent_id TEXT NOT NULL REFERENCES agents(id), model_id TEXT NOT NULL DEFAULT 'deepseek-chat', title TEXT NOT NULL, preview TEXT NOT NULL,
              created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, role TEXT NOT NULL,
              type TEXT NOT NULL, content TEXT NOT NULL, audio BLOB, mime_type TEXT, duration REAL, created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS messages_session_created ON messages(session_id, created_at);
            CREATE INDEX IF NOT EXISTS sessions_updated ON sessions(updated_at DESC);
            CREATE TABLE IF NOT EXISTS models (id TEXT PRIMARY KEY, name TEXT NOT NULL, provider TEXT NOT NULL, base_url TEXT NOT NULL DEFAULT '', request_path TEXT NOT NULL DEFAULT '/chat/completions', api_key TEXT NOT NULL DEFAULT '', model TEXT NOT NULL, built_in INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS providers (id TEXT PRIMARY KEY, name TEXT NOT NULL, api TEXT NOT NULL DEFAULT 'openai-completions', base_url TEXT NOT NULL DEFAULT '', api_key TEXT NOT NULL DEFAULT '', built_in INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
        """)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(agents)")}
        if "request_path" not in columns:
            conn.execute("ALTER TABLE agents ADD COLUMN request_path TEXT NOT NULL DEFAULT '/chat/completions'")
        if "api_key" not in columns:
            conn.execute("ALTER TABLE agents ADD COLUMN api_key TEXT NOT NULL DEFAULT ''")
        session_columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
        if "model_id" not in session_columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN model_id TEXT NOT NULL DEFAULT 'deepseek-chat'")
        model_columns = {row[1] for row in conn.execute("PRAGMA table_info(models)")}
        if "provider_id" not in model_columns:
            conn.execute("ALTER TABLE models ADD COLUMN provider_id TEXT NOT NULL DEFAULT 'deepseek'")
        conn.execute("INSERT OR IGNORE INTO providers VALUES (:id,:name,:api,:base_url,:api_key,:built_in,:created_at,:updated_at)", DEFAULT_PROVIDER)
        conn.execute("""INSERT OR IGNORE INTO models (id,name,provider_id,provider,base_url,request_path,api_key,model,built_in,created_at,updated_at)
            VALUES (:id,:name,:provider_id,:provider,:base_url,:request_path,:api_key,:model,:built_in,:created_at,:updated_at)""", {**DEFAULT_MODEL, "provider_id": DEFAULT_PROVIDER_ID})
        # Migrate each historical Agent connection into a separate reusable model profile.
        for row in conn.execute("SELECT * FROM agents").fetchall():
            legacy_id = f"legacy-model-{row[0]}"
            conn.execute("""INSERT OR IGNORE INTO models (id,name,provider_id,provider,base_url,request_path,api_key,model,built_in,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (legacy_id, f"{row[1]} model", legacy_id, row[4], row[5], row[6], row[7], row[8], 0, row[12], row[13]))
            conn.execute("UPDATE sessions SET model_id=? WHERE agent_id=? AND model_id=?", (legacy_id, row[0], DEFAULT_MODEL_ID))
        conn.execute("""INSERT OR IGNORE INTO agents (id, name, description, system_prompt, provider, base_url, request_path, api_key, model,
            language, voice, built_in, created_at, updated_at) VALUES (:id, :name, :description, :system_prompt, :provider, :base_url,
            :request_path, :api_key, :model, :language, :voice, :built_in, :created_at, :updated_at)""", DEFAULT_AGENT)
        conn.execute("UPDATE agents SET system_prompt='' WHERE id=?", (DEFAULT_AGENT_ID,))
        # Old releases stored endpoint credentials on each model. Materialise one Provider per
        # old connection profile so key material becomes provider-owned without losing sessions.
        for row in conn.execute("SELECT * FROM models").fetchall():
            provider_id = row["provider_id"] or (DEFAULT_PROVIDER_ID if row["id"] == DEFAULT_MODEL_ID else f"legacy-provider-{row['id']}")
            if row["id"] == DEFAULT_MODEL_ID:
                provider_id = DEFAULT_PROVIDER_ID
            elif provider_id == DEFAULT_PROVIDER_ID and (row["base_url"] or row["api_key"]):
                provider_id = f"legacy-provider-{row['id']}"
            provider = {
                "id": provider_id,
                "name": "DeepSeek" if provider_id == DEFAULT_PROVIDER_ID else f"{row['name']} provider",
                "api": "openai-completions",
                "base_url": row["base_url"], "api_key": row["api_key"],
                "built_in": int(provider_id == DEFAULT_PROVIDER_ID),
                "created_at": row["created_at"], "updated_at": row["updated_at"],
            }
            conn.execute("INSERT OR IGNORE INTO providers VALUES (:id,:name,:api,:base_url,:api_key,:built_in,:created_at,:updated_at)", provider)
            conn.execute("UPDATE models SET provider_id=?, base_url='', api_key='' WHERE id=?", (provider_id, row["id"]))
        conn.execute("CREATE INDEX IF NOT EXISTS models_provider ON models(provider_id)")
        conn.execute(
            """UPDATE messages SET type='thinking'
               WHERE role='assistant' AND type='text'
                 AND content LIKE 'Here''s a thinking process:%'"""
        )
        conn.execute(
            """UPDATE sessions
               SET preview=COALESCE((
                   SELECT substr(content, 1, 62) FROM messages
                   WHERE session_id=sessions.id AND type!='thinking'
                   ORDER BY created_at DESC LIMIT 1
               ), 'Thinking')
               WHERE preview LIKE 'Here''s a thinking process:%'"""
        )
        _repair_misaligned_sessions(conn)


def conversation_title(content: str) -> str:
    summary = " ".join(content.split()).strip()
    if summary.casefold().rstrip("!！。?.？") in {"hi", "hello", "hey", "你好", "您好", "在吗"}:
        return "Greeting / 问候"
    return summary[:34] or "New conversation / 新会话"


def _repair_misaligned_sessions(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT * FROM sessions WHERE typeof(created_at) != 'integer'").fetchall()
    for session in rows:
        user_messages = conn.execute(
            "SELECT content,created_at FROM messages WHERE session_id=? AND role='user' ORDER BY created_at",
            (session["id"],),
        ).fetchall()
        meaningful = next((row for row in user_messages if conversation_title(row["content"]) != "Greeting / 问候"), None)
        first = meaningful or (user_messages[0] if user_messages else None)
        last = conn.execute(
            "SELECT content FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT 1",
            (session["id"],),
        ).fetchone()
        model_id = session["model_id"]
        if not conn.execute("SELECT 1 FROM models WHERE id=?", (model_id,)).fetchone():
            model_id = DEFAULT_MODEL_ID
        created_at = first["created_at"] if first else session["updated_at"]
        conn.execute(
            "UPDATE sessions SET model_id=?,title=?,preview=?,created_at=? WHERE id=?",
            (
                model_id,
                conversation_title(first["content"]) if first else "New conversation / 新会话",
                " ".join(last["content"].split())[:62] if last else "No messages yet / 暂无消息",
                created_at,
                session["id"],
            ),
        )


def normalise_agent(data: dict, identifier: str, built_in: bool, created_at: int) -> dict:
    timestamp = now_ms()
    return {
        "id": identifier, "name": str(data.get("name", "")).strip(), "description": str(data.get("description", "")),
        "system_prompt": str(data.get("systemPrompt", data.get("system_prompt", ""))),
        "provider": str(data.get("provider", "custom")), "base_url": str(data.get("baseUrl", data.get("base_url", ""))),
        "request_path": str(data.get("requestPath", data.get("request_path", "/chat/completions"))) or "/chat/completions",
        "api_key": str(data.get("apiKey", data.get("api_key", ""))),
        "model": str(data.get("model", "")), "language": str(data.get("language", "Auto")), "voice": str(data.get("voice", "Auto")),
        "built_in": int(built_in), "created_at": created_at, "updated_at": timestamp,
    }


def normalise_model(data: dict, identifier: str, built_in: bool, created_at: int) -> dict:
    return {"id": identifier, "provider_id": str(data.get("providerId", data.get("provider_id", DEFAULT_PROVIDER_ID))), "name": str(data.get("name", "")).strip(), "provider": str(data.get("provider", "custom")), "base_url": str(data.get("baseUrl", data.get("base_url", ""))), "request_path": str(data.get("requestPath", data.get("request_path", "/chat/completions"))) or "/chat/completions", "api_key": str(data.get("apiKey", data.get("api_key", ""))), "model": str(data.get("model", "")).strip(), "built_in": int(built_in), "created_at": created_at, "updated_at": now_ms()}


def normalise_provider(data: dict, identifier: str, built_in: bool, created_at: int) -> dict:
    return {
        "id": identifier, "name": str(data.get("name", "")).strip(),
        "api": str(data.get("api", "openai-completions")).strip() or "openai-completions",
        "base_url": str(data.get("baseUrl", data.get("base_url", ""))).strip().rstrip("/"),
        "api_key": str(data.get("apiKey", data.get("api_key", ""))).strip(),
        "built_in": int(built_in), "created_at": created_at, "updated_at": now_ms(),
    }


def fetch_agent(database_path: str, agent_id: str) -> dict:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        return row_to_agent(conn.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone())


def fetch_session(database_path: str, session_id: str) -> dict:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        return row_to_session(conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone())

def fetch_model(database_path: str, model_id: str) -> dict:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        return row_to_model(conn.execute("SELECT * FROM models WHERE id=?", (model_id,)).fetchone())


def fetch_provider(database_path: str, provider_id: str) -> dict:
    with sqlite3.connect(database_path) as conn:
        conn.row_factory = sqlite3.Row
        return row_to_provider(conn.execute("SELECT * FROM providers WHERE id=?", (provider_id,)).fetchone())


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
    if str(data.get("role", "user")) == "user" and session["title"] in {"New conversation / 新会话", "Greeting / 问候"}:
        title = conversation_title(content)
    conn.execute("UPDATE sessions SET title = ?, preview = ?, updated_at = ? WHERE id = ?", (title, summary[:62], timestamp, session["id"]))
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (identifier,)).fetchone()
    return row_to_message(row)


def format_duration(seconds: float | int | None) -> str:
    value = max(0, round(float(seconds or 0)))
    return f"{value // 60:02d}:{value % 60:02d}"


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8002, debug=False)
