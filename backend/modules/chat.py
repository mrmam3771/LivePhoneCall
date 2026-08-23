from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status

from chat_store import (
    DEFAULT_AGENT_ID,
    DEFAULT_DATABASE_PATH,
    DEFAULT_MODEL_ID,
    DEFAULT_PROVIDER_ID,
    fetch_agent,
    fetch_model,
    fetch_provider,
    fetch_session,
    initialise_database,
    insert_message,
    normalise_agent,
    normalise_model,
    normalise_provider,
    now_ms,
    row_to_agent,
    row_to_message,
    row_to_model,
    row_to_provider,
    row_to_session,
)


router = APIRouter(prefix="/api/chat", tags=["chat"])


def initialize() -> None:
    initialise_database(DEFAULT_DATABASE_PATH)


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DEFAULT_DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def require_row(connection: sqlite3.Connection, table: str, identifier: str, message: str) -> sqlite3.Row:
    row = connection.execute(f"SELECT * FROM {table} WHERE id=?", (identifier,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=message)
    return row


@router.get("/health")
def health() -> dict[str, Any]:
    return {"ready": True, "database": DEFAULT_DATABASE_PATH.name}


@router.get("/bootstrap")
def bootstrap() -> dict[str, Any]:
    with connect() as connection:
        return {
            "agents": [row_to_agent(row) for row in connection.execute("SELECT * FROM agents ORDER BY built_in DESC, updated_at DESC")],
            "providers": [row_to_provider(row) for row in connection.execute("SELECT * FROM providers ORDER BY built_in DESC, updated_at DESC")],
            "models": [row_to_model(row) for row in connection.execute("SELECT * FROM models ORDER BY built_in DESC, updated_at DESC")],
            "sessions": [row_to_session(row) for row in connection.execute("SELECT * FROM sessions ORDER BY updated_at DESC")],
        }


@router.get("/providers")
def list_providers() -> list[dict]:
    with connect() as connection:
        return [row_to_provider(row) for row in connection.execute("SELECT * FROM providers ORDER BY built_in DESC, updated_at DESC")]


@router.post("/providers", status_code=status.HTTP_201_CREATED)
def create_provider(data: dict) -> dict:
    if not str(data.get("name", "")).strip():
        raise HTTPException(status_code=400, detail="Provider name is required")
    identifier, timestamp = str(uuid.uuid4()), now_ms()
    provider = normalise_provider(data, identifier, False, timestamp)
    with connect() as connection:
        connection.execute("INSERT INTO providers VALUES (:id,:name,:api,:base_url,:api_key,:built_in,:created_at,:updated_at)", provider)
    return fetch_provider(str(DEFAULT_DATABASE_PATH), identifier)


@router.put("/providers/{provider_id}")
def update_provider(provider_id: str, data: dict) -> dict:
    with connect() as connection:
        existing = require_row(connection, "providers", provider_id, "Provider not found")
        provider = normalise_provider({**row_to_provider(existing), **data}, provider_id, bool(existing["built_in"]), existing["created_at"])
        connection.execute("UPDATE providers SET name=:name,api=:api,base_url=:base_url,api_key=:api_key,updated_at=:updated_at WHERE id=:id", provider)
    return fetch_provider(str(DEFAULT_DATABASE_PATH), provider_id)


@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_provider(provider_id: str) -> Response:
    if provider_id == DEFAULT_PROVIDER_ID:
        raise HTTPException(status_code=400, detail="The built-in provider cannot be deleted")
    with connect() as connection:
        require_row(connection, "providers", provider_id, "Provider not found")
        if connection.execute("SELECT 1 FROM models WHERE provider_id=?", (provider_id,)).fetchone():
            raise HTTPException(status_code=400, detail="Delete or move this provider's models first")
        connection.execute("DELETE FROM providers WHERE id=?", (provider_id,))
    return Response(status_code=204)


@router.get("/models")
def list_models() -> list[dict]:
    with connect() as connection:
        return [row_to_model(row) for row in connection.execute("SELECT * FROM models ORDER BY built_in DESC, updated_at DESC")]


@router.post("/models", status_code=status.HTTP_201_CREATED)
def create_model(data: dict) -> dict:
    if not str(data.get("name", "")).strip() or not str(data.get("model", "")).strip():
        raise HTTPException(status_code=400, detail="Model name and model identifier are required")
    identifier, timestamp = str(uuid.uuid4()), now_ms()
    model = normalise_model(data, identifier, False, timestamp)
    with connect() as connection:
        require_row(connection, "providers", model["provider_id"], "Selected provider does not exist")
        connection.execute("INSERT INTO models (id,name,provider_id,provider,base_url,request_path,api_key,model,built_in,created_at,updated_at) VALUES (:id,:name,:provider_id,:provider,:base_url,:request_path,:api_key,:model,:built_in,:created_at,:updated_at)", model)
    return fetch_model(str(DEFAULT_DATABASE_PATH), identifier)


@router.put("/models/{model_id}")
def update_model(model_id: str, data: dict) -> dict:
    with connect() as connection:
        existing = require_row(connection, "models", model_id, "Model profile not found")
        model = normalise_model({**row_to_model(existing), **data}, model_id, bool(existing["built_in"]), existing["created_at"])
        require_row(connection, "providers", model["provider_id"], "Selected provider does not exist")
        connection.execute("UPDATE models SET name=:name,provider_id=:provider_id,provider=:provider,base_url=:base_url,request_path=:request_path,api_key=:api_key,model=:model,updated_at=:updated_at WHERE id=:id", model)
    return fetch_model(str(DEFAULT_DATABASE_PATH), model_id)


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: str) -> Response:
    if model_id == DEFAULT_MODEL_ID:
        raise HTTPException(status_code=400, detail="The built-in model cannot be deleted")
    with connect() as connection:
        require_row(connection, "models", model_id, "Model profile not found")
        connection.execute("UPDATE sessions SET model_id=? WHERE model_id=?", (DEFAULT_MODEL_ID, model_id))
        connection.execute("DELETE FROM models WHERE id=?", (model_id,))
    return Response(status_code=204)


@router.get("/agents")
def list_agents() -> list[dict]:
    with connect() as connection:
        return [row_to_agent(row) for row in connection.execute("SELECT * FROM agents ORDER BY built_in DESC, updated_at DESC")]


@router.post("/agents", status_code=status.HTTP_201_CREATED)
def create_agent(data: dict) -> dict:
    if not str(data.get("name", "")).strip():
        raise HTTPException(status_code=400, detail="Agent name is required")
    identifier, timestamp = str(uuid.uuid4()), now_ms()
    agent = normalise_agent(data, identifier, False, timestamp)
    with connect() as connection:
        connection.execute("""INSERT INTO agents (id,name,description,system_prompt,provider,base_url,request_path,api_key,model,language,voice,built_in,created_at,updated_at)
            VALUES (:id,:name,:description,:system_prompt,:provider,:base_url,:request_path,:api_key,:model,:language,:voice,:built_in,:created_at,:updated_at)""", agent)
    return fetch_agent(str(DEFAULT_DATABASE_PATH), identifier)


@router.put("/agents/{agent_id}")
def update_agent(agent_id: str, data: dict) -> dict:
    with connect() as connection:
        existing = require_row(connection, "agents", agent_id, "Agent not found")
        agent = normalise_agent({**row_to_agent(existing), **data}, agent_id, bool(existing["built_in"]), existing["created_at"])
        connection.execute("""UPDATE agents SET name=:name,description=:description,system_prompt=:system_prompt,provider=:provider,base_url=:base_url,request_path=:request_path,api_key=:api_key,model=:model,language=:language,voice=:voice,updated_at=:updated_at WHERE id=:id""", agent)
    return fetch_agent(str(DEFAULT_DATABASE_PATH), agent_id)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str) -> Response:
    if agent_id == DEFAULT_AGENT_ID:
        raise HTTPException(status_code=400, detail="The built-in Agent cannot be deleted")
    with connect() as connection:
        require_row(connection, "agents", agent_id, "Agent not found")
        connection.execute("UPDATE sessions SET agent_id=? WHERE agent_id=?", (DEFAULT_AGENT_ID, agent_id))
        connection.execute("DELETE FROM agents WHERE id=?", (agent_id,))
    return Response(status_code=204)


@router.get("/sessions")
def list_sessions() -> list[dict]:
    with connect() as connection:
        return [row_to_session(row) for row in connection.execute("SELECT * FROM sessions ORDER BY updated_at DESC")]


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(data: dict) -> dict:
    agent_id = data.get("agentId", data.get("agent_id", DEFAULT_AGENT_ID))
    model_id = data.get("modelId", data.get("model_id", DEFAULT_MODEL_ID))
    identifier, timestamp = str(uuid.uuid4()), now_ms()
    with connect() as connection:
        require_row(connection, "agents", agent_id, "Selected Agent does not exist")
        require_row(connection, "models", model_id, "Selected model does not exist")
        connection.execute("""INSERT INTO sessions (id,agent_id,model_id,title,preview,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?)""", (identifier, agent_id, model_id, "New conversation / 新会话", "No messages yet / 暂无消息", timestamp, timestamp))
    return fetch_session(str(DEFAULT_DATABASE_PATH), identifier)


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, data: dict) -> dict:
    agent_id, model_id = data.get("agentId", data.get("agent_id")), data.get("modelId", data.get("model_id"))
    if not agent_id and not model_id:
        raise HTTPException(status_code=400, detail="agentId or modelId is required")
    with connect() as connection:
        existing = require_row(connection, "sessions", session_id, "Conversation not found")
        if agent_id:
            require_row(connection, "agents", agent_id, "Selected Agent does not exist")
        if model_id:
            require_row(connection, "models", model_id, "Selected model does not exist")
        connection.execute("UPDATE sessions SET agent_id=?,model_id=?,updated_at=? WHERE id=?", (agent_id or existing["agent_id"], model_id or existing["model_id"], now_ms(), session_id))
    return fetch_session(str(DEFAULT_DATABASE_PATH), session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str) -> Response:
    with connect() as connection:
        require_row(connection, "sessions", session_id, "Conversation not found")
        connection.execute("DELETE FROM sessions WHERE id=?", (session_id,))
    return Response(status_code=204)


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str) -> list[dict]:
    with connect() as connection:
        require_row(connection, "sessions", session_id, "Conversation not found")
        return [row_to_message(row) for row in connection.execute("SELECT * FROM messages WHERE session_id=? ORDER BY created_at", (session_id,))]


@router.post("/sessions/{session_id}/messages", status_code=status.HTTP_201_CREATED)
def add_message(session_id: str, data: dict) -> dict:
    with connect() as connection:
        session = require_row(connection, "sessions", session_id, "Conversation not found")
        try:
            return insert_message(connection, session, data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
