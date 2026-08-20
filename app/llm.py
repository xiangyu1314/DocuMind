"""DeepSeek 大模型客户端封装（阶段①）。

用 openai SDK 对接 DeepSeek —— DeepSeek 提供 OpenAI 兼容接口，
所以同一个 SDK 既能调 OpenAI 也能调 DeepSeek，只差 base_url 和 key。

后续阶段②（function calling）、③（RAG）、⑤（SSE 流式）都会在这里扩展，
或新增方法，保持「大模型相关逻辑」都收拢在本模块。
"""
from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


class DeepSeekClient:
    """对 DeepSeek 的 chat 接口做一层薄封装。

    好处：
    1. 「在哪调、用什么模型」集中一处，换模型/加参数只改这里；
    2. 调用方只关心 messages 和拿到文本，不用关心 SDK 细节。
    """

    def __init__(self) -> None:
        # DeepSeek 用 OpenAI 兼容协议，直接复用 openai SDK
        self._client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
        self.model = DEEPSEEK_MODEL

    def complete(self, messages: list[dict], **kwargs):
        """发一轮对话，返回完整的 assistant message 对象。

        阶段② function calling 需要读取 message.tool_calls，
        所以不能只返回文本，得把整个 message 交出来。
        """
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message

    def chat(self, messages: list[dict], **kwargs) -> str:
        """发一轮对话，返回助手回复文本。

        messages 形如 [{"role": "user", "content": "你好"}]。
        多轮对话 = 把历史问答也放进 messages（阶段①冒烟测试里会演示）。
        """
        return self.complete(messages, **kwargs).content

    def stream(self, messages: list[dict], **kwargs):
        """返回流式响应（生成器），供 SSE 逐 token 输出用。

        调用方用 `for chunk in client.stream(...)` 遍历，每个 chunk 是
        openai SDK 的流式片段（含 delta.content / delta.tool_calls）。
        """
        return self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            **kwargs,
        )


# 模块级单例：整个项目共用一个客户端（省去反复创建连接）
client = DeepSeekClient()
