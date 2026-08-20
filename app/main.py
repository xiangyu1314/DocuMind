"""知枢 FastAPI 服务（阶段④+⑤）：把 Agent 包装成 HTTP 接口。

启动（在项目根目录 DocuMind 下）：
    uvicorn app.main:app --reload

接口：
    POST /chat              —— 一次性返回完整答案（JSON），可传 session_id 持久化
    POST /chat/stream       —— SSE 流式，逐 token 输出，可传 session_id 持久化
    POST /sessions          —— 新建会话
    GET  /sessions          —— 列出所有会话
    GET  /sessions/{id}     —— 取某会话全部消息
    DELETE /sessions/{id}   —— 删除会话
"""
import json
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import ensure_config
from app.agent import run_agent, run_agent_stream
from app.session_store import (
    add_message,
    create_session,
    delete_session,
    get_messages,
    list_sessions,
)

ensure_config()

app = FastAPI(title="知枢 DocuMind", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None  # 传入则把本轮对话持久化到该会话


class SessionCreate(BaseModel):
    title: str = "新会话"


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    """普通接口：返回完整答案；传 session_id 则持久化多轮对话。"""
    history = None
    if req.session_id is not None:
        history = get_messages(req.session_id)
        add_message(req.session_id, "user", req.message)

    answer = run_agent(req.message, history=history)

    if req.session_id is not None:
        add_message(req.session_id, "assistant", answer)

    return {"answer": answer, "session_id": req.session_id}


@app.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """SSE 流式接口：token 一个个往外推；传 session_id 则持久化。"""
    history = None
    if req.session_id is not None:
        history = get_messages(req.session_id)
        add_message(req.session_id, "user", req.message)

    def event_stream():
        parts: list[str] = []
        for token in run_agent_stream(req.message, history=history):
            parts.append(token)
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        if req.session_id is not None:
            add_message(req.session_id, "assistant", "".join(parts))
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/sessions")
def create_session_api(req: SessionCreate) -> dict:
    """新建会话。"""
    sid = create_session(req.title)
    return {"session_id": sid, "title": req.title}


@app.get("/sessions")
def list_sessions_api() -> list[dict]:
    """列出所有会话（按最近更新倒序）。"""
    return list_sessions()


@app.get("/sessions/{session_id}")
def get_session_api(session_id: int) -> dict:
    """取某会话的全部消息。"""
    return {"session_id": session_id, "messages": get_messages(session_id)}


@app.delete("/sessions/{session_id}")
def delete_session_api(session_id: int) -> dict:
    """删除会话及其消息。"""
    delete_session(session_id)
    return {"deleted": session_id}
