"""知枢 FastAPI 服务（阶段④）：把 Agent 包装成 HTTP 接口。

启动（在项目根目录 DocuMind 下）：
    uvicorn app.main:app --reload

接口：
    POST /chat          —— 一次性返回完整答案（JSON）
    POST /chat/stream   —— SSE 流式，逐 token 输出
"""
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import ensure_config
from app.agent import run_agent, run_agent_stream

ensure_config()

app = FastAPI(title="知枢 DocuMind", version="0.1.0")


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    """普通接口：返回完整答案。"""
    return {"answer": run_agent(req.message)}


@app.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """SSE 流式接口：token 一个个往外推。"""

    def event_stream():
        for token in run_agent_stream(req.message):
            # SSE 格式：每个事件一行 `data: {...}`
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
