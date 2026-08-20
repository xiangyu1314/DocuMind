"""知枢 DocuMind 的 Gradio 前端（阶段⑤）。

一条命令启动可视化聊天界面：
    python app/gradio_app.py
然后浏览器打开 http://127.0.0.1:7860

两个页签：
    「对话」    —— 多轮聊天 + 会话管理（新建 / 切换 / 删除，历史存 MySQL）
    「文档入库」 —— 输入文档路径，解析并向量化入库

设计：Gradio 进程内直接调用 agent 的流式循环 run_agent_stream；
多轮历史从 MySQL 会话表读取，刷新 / 重启后历史仍在。
（前后端分层版见 app/main.py 的 FastAPI 接口，两者共用同一个 agent。）
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
import gradio_client.utils as _gcu

# 修复 gradio 4.44.1 + gradio_client 1.3.0 的 schema 解析 bug：
# JSON Schema 里布尔值 schema 是合法的（true=任意类型），但 gradio_client 没处理；
# 组件同时作为事件的「输入 + 输出」时（例如 Chatbot 边收历史边流式回写、State 存会话 id），
# 生成的 schema 会带 additionalProperties: true，get_api_info() 里 `"const" in True`
# 直接 TypeError。这里 monkey-patch 补上布尔分支，让 api_info 生成不再崩。
_orig_json_schema_to_python_type = _gcu._json_schema_to_python_type


def _patched_json_schema_to_python_type(schema, defs):
    if schema is True:
        return "Any"
    if schema is False:
        return "None"
    return _orig_json_schema_to_python_type(schema, defs)


_gcu._json_schema_to_python_type = _patched_json_schema_to_python_type

from app.agent import run_agent_stream
from app.rag import index_file
from app.session_store import (
    add_message,
    create_session,
    delete_session,
    get_messages,
    list_sessions,
)


def _session_choices():
    """生成会话下拉框选项 [(label, id), ...]，按最近更新倒序。"""
    return [(f"#{s['id']} {s['title']}", s["id"]) for s in list_sessions()]


def _db_to_chatbot(messages):
    """把 [{role, content}, ...] 转成 Chatbot 的 [(user, bot), ...] 格式。"""
    pairs = []
    for m in messages:
        if m["role"] == "user":
            pairs.append([m["content"], None])
        elif pairs and pairs[-1][1] is None:
            pairs[-1][1] = m["content"]
        else:
            pairs.append([None, m["content"]])
    return pairs


def on_new():
    """新建会话：建一条记录、切换过去、清空聊天区。"""
    sid = create_session("新会话")
    return sid, gr.Dropdown(choices=_session_choices(), value=sid), []


def on_delete(sid):
    """删除当前会话。"""
    if sid is not None:
        delete_session(sid)
    return None, gr.Dropdown(choices=_session_choices(), value=None), []


def on_select(sid):
    """切换到某会话：从 MySQL 加载其历史。"""
    if sid is None:
        return None, []
    return sid, _db_to_chatbot(get_messages(sid))


def on_submit(sid, message, history):
    """发送消息：流式回答，并把本轮对话持久化到 MySQL。"""
    message = (message or "").strip()
    if not message:
        yield sid, history
        return

    if sid is None:
        # 没选会话时，自动用首条消息建一个会话
        sid = create_session(message[:20] or "新会话")

    prior = get_messages(sid)           # 之前的历史（不含本条）
    add_message(sid, "user", message)   # 存用户消息

    history = history + [[message, None]]
    yield sid, history                  # 先把用户气泡显示出来

    full = ""
    for token in run_agent_stream(message, history=prior):
        full += token
        history[-1][1] = full
        yield sid, history              # 逐 token 更新回答气泡

    add_message(sid, "assistant", full)  # 存助手消息


def _refresh_dd(sid):
    """提交完成后刷新会话列表（新建的会话 / 更新的排序要反映出来）。"""
    return gr.Dropdown(choices=_session_choices(), value=sid)


def upload_and_index(filepath):
    """文档入库回调：解析 -> 切块 -> 向量化 -> 写入 Qdrant。"""
    if not filepath:
        return "请先输入文档路径。"
    try:
        n = index_file(filepath)
        return f"✅ 已解析并入库 {n} 个文本块。现在去「对话」页提问即可。"
    except Exception as e:  # noqa: BLE001 —— 把解析/入库错误如实反馈给用户
        return f"❌ 入库失败：{e}"


with gr.Blocks(title="知枢 · DocuMind") as chat_ui:
    sid_state = gr.State(None)

    with gr.Row():
        session_dd = gr.Dropdown(label="会话", choices=_session_choices(), interactive=True)
        new_btn = gr.Button("新建会话")
        del_btn = gr.Button("删除会话")

    chatbot = gr.Chatbot(height=480)
    msg = gr.Textbox(label="输入", placeholder="输入问题后回车…", lines=1)

    # 事件绑定
    submit_evt = msg.submit(on_submit, [sid_state, msg, chatbot], [sid_state, chatbot])
    submit_evt.then(_refresh_dd, [sid_state], [session_dd])  # 发完刷新会话列表
    msg.submit(lambda: "", None, msg)                        # 发完清空输入框
    new_btn.click(on_new, None, [sid_state, session_dd, chatbot])
    del_btn.click(on_delete, [sid_state], [sid_state, session_dd, chatbot])
    session_dd.change(on_select, [session_dd], [sid_state, chatbot])


upload_ui = gr.Interface(
    fn=upload_and_index,
    inputs=gr.Textbox(
        label="文档路径",
        placeholder="例如：D:/NLPCode/DocuMind/data/考勤制度.md",
        lines=1,
    ),
    outputs="text",
    title="知识库入库",
    description=(
        "输入文档的绝对路径，自动解析并向量化入库。支持 Markdown / 纯文本 / Word / PDF。\n"
        "（也可命令行批量入库：`python scripts/ingest_file.py <路径>`）"
    ),
)

# 说明：入库页用 gr.Textbox 输入路径，而非 gr.File 上传按钮。
# gradio 4.44.1 + gradio_client 1.3.0 有 schema 解析 bug（additionalProperties 被当成
# bool 传给 json_schema_to_python_type），TabbedInterface 里一放 gr.File 就会在
# get_api_info 时崩（TypeError: argument of type 'bool' is not iterable）。
# Textbox 走纯字符串 schema，不受影响；命令行批量入库走 scripts/ingest_file.py。
app = gr.TabbedInterface([chat_ui, upload_ui], ["对话", "文档入库"])


if __name__ == "__main__":
    app.launch(server_name="127.0.0.1", server_port=7860, show_error=True)
