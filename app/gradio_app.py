"""知枢 DocuMind 的 Gradio 前端（阶段⑤）。

一条命令启动可视化聊天界面：
    python app/gradio_app.py
然后浏览器打开 http://127.0.0.1:7860

设计：Gradio 进程内直接调用 agent 的流式循环 run_agent_stream，
把上一轮对话压成 history 传回去，实现多轮记忆 + 逐 token 流式输出。
（前后端分层版见 app/main.py 的 FastAPI SSE 接口，两者共用同一个 agent。）
"""
import os
import sys
from pathlib import Path

# 允许 `python app/gradio_app.py` 直接运行：把项目根目录放进 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 必须在 import gradio 之前设好：gradio 会连带 import huggingface_hub，
# 后者在 import 时就固化 HF_ENDPOINT 与离线开关，之后再设就晚了。
# bge 模型已缓存在本地（~/.cache/huggingface），离线加载最快最稳、不碰网络无 SSL 问题；
# 换新机器要重新下载时，删掉下面两行离线开关即可改走 hf-mirror 镜像。
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import gradio as gr

from app.agent import run_agent_stream


def respond(message: str, history):
    """ChatInterface 回调：把 Gradio 的历史转成 messages，流式吐出最终答案。

    history 是 [(user, bot), ...] 列表，这里压成 OpenAI 风格的对话；
    只保留最终答案（不重放历史中的工具调用过程）作多轮上下文。
    """
    messages = []
    for user, bot in history:
        if user is not None:
            messages.append({"role": "user", "content": user})
        if bot is not None:
            messages.append({"role": "assistant", "content": bot})

    full = ""
    for token in run_agent_stream(message, history=messages):
        full += token
        yield full


demo = gr.ChatInterface(
    fn=respond,
    title="知枢 · DocuMind",
    description=(
        "本地知识库智能问答 Agent —— **手写** RAG + Function Calling，"
        "不依赖 LangChain / LlamaIndex / Dify。\n\n"
        "三件事能自动路由：算术计算、查 MySQL（商品/库存）、查知识库文档（带引用）。"
    ),
    examples=[
        "帮我算 12.5 * 8 + 3 等于多少？",
        "查一下所有商品，按价格从高到低排",
        "公司年假有多少天？",
    ],
    theme="soft",
    chatbot=gr.Chatbot(height=520),
)


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, show_error=True)
