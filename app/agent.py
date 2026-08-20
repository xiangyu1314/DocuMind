"""Agent 核心循环（阶段②）—— 手写 function calling 的多轮工具调用。

这是整个项目的灵魂：模型与工具之间来回"对讲"的循环。
模型不会执行工具，它只会"喊"要调哪个、传什么参数；执行的是我们，
再把结果以 role="tool" 喂回去，直到模型给出最终答案。

这就是 ReAct（推理 + 行动）循环的雏形：观察 -> 行动 -> 观察 -> ... -> 回答。
"""
from typing import Optional

from app.llm import client
from app.tools import TOOLS, execute_tool

# 最多来回几轮，防止模型一直喊工具导致死循环
MAX_ROUNDS = 5

DEFAULT_SYSTEM_PROMPT = (
    "你是知枢，一个严谨、简洁的中文助手。你可以调用工具来回答问题："
    "算术用 calculate，查结构化数据（商品/库存）用 query_db，"
    "查文档/制度/知识内容用 search_knowledge_base。拿到结果后再回答。"
)


def run_agent(
    user_msg: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    verbose: bool = False,
    history: Optional[list] = None,
) -> str:
    """一轮 Agent 循环：用户提问 ->（可能多次）调用工具 -> 最终回答。

    verbose=True 时打印每一步工具调用的细节，便于观察中间过程。
    history 传入之前的对话（[{"role":..., "content":...}, ...]）以支持多轮。
    """
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_msg})

    for _ in range(MAX_ROUNDS):
        # 每轮都带 tools 一起发：让模型决定「直接回答」还是「喊工具」
        msg = client.complete(messages, tools=TOOLS)

        # 没有 tool_calls -> 模型已经给出最终答案，直接返回
        if not msg.tool_calls:
            return msg.content

        # 有 tool_calls -> 先把模型这条（含 tool_calls 的）消息放回上下文
        messages.append(msg)

        # 逐个执行模型要求的工具，并把结果以 role="tool" 追加回去
        for tc in msg.tool_calls:
            result = execute_tool(tc.function.name, tc.function.arguments)
            if verbose:
                print(f"    [工具调用] {tc.function.name}({tc.function.arguments}) -> {result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,  # 必须与模型给的 id 对上
                    "content": result,
                }
            )

    return "达到最大工具调用轮数，仍未得到最终答案。"


def run_agent_stream(
    user_msg: str,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    history: Optional[list] = None,
):
    """run_agent 的流式版：逐 token yield 最终答案，工具调用过程不产出文本。

    与 run_agent 同一套逻辑，区别是每轮都走流式：
    - 工具调用轮：只收到 tool_calls 分片（无文本），执行后继续下一轮；
    - 最终回答轮：收到 delta.content，逐个 token yield 出去。
    history 传入之前的对话以支持多轮。
    """
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_msg})

    for _ in range(MAX_ROUNDS):
        stream = client.stream(messages, tools=TOOLS)
        tool_calls: dict[int, dict] = {}  # index -> {id, name, arguments}
        content_parts: list[str] = []     # 缓冲本轮的文本（可能是"思考"或最终答案）

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            # 先缓冲文本，不立即 yield —— 因为若本轮后面跟着工具调用，
            # 这段文本只是模型的"思考"（如"我需要查询知识库"），不能泄露给用户
            if delta.content:
                content_parts.append(delta.content)

            # 工具调用：arguments 是一段段拼起来的碎片，按 index 累积
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    e = tool_calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                    if tc.id:
                        e["id"] = tc.id
                    if tc.function and tc.function.name:
                        e["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        e["arguments"] += tc.function.arguments

        if not tool_calls:
            # 本轮是最终回答：把缓冲的文本逐 token yield 出去
            for part in content_parts:
                yield part
            return

        # 本轮是工具调用：丢弃 content_parts（模型的"思考"），执行工具后继续
        print(
            "[流式·工具调用] " + ", ".join(e["name"] for _, e in sorted(tool_calls.items())),
            flush=True,
        )
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": e["id"], "type": "function",
                     "function": {"name": e["name"], "arguments": e["arguments"]}}
                    for _, e in sorted(tool_calls.items())
                ],
            }
        )
        for _, e in sorted(tool_calls.items()):
            result = execute_tool(e["name"], e["arguments"])
            messages.append({"role": "tool", "tool_call_id": e["id"], "content": result})

    yield "\n\n[达到最大工具调用轮数]"
