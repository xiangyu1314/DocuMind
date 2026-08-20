"""阶段① 冒烟测试：验证 DeepSeek API 已跑通。

运行（在项目根目录 DocuMind 下）：
    conda activate NLP
    python scripts/phase1_smoke.py

会依次演示：
1. 带 system prompt 的单轮对话；
2. 多轮对话 —— 对比「不带历史」vs「带历史」，直观理解
   大模型本身无记忆，上下文全靠调用方把历史塞进 messages。
"""
import sys
from pathlib import Path

# 脚本在子目录里，把项目根目录加到 sys.path，才能 import config / app
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ensure_config

ensure_config()  # 先校验 key，报错信息更清晰

from app.llm import client  # 通过校验后再建客户端


def main() -> None:
    print("=== 阶段①：DeepSeek API 冒烟测试 ===\n")

    system_prompt = "你是知枢，一个严谨、简洁的中文知识问答助手。"

    # 1) 单轮
    reply = client.chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "用一句话介绍你自己，并说明你能做什么。"},
        ]
    )
    print(f"[单轮] {reply}\n")

    # 2) 多轮 —— 不带历史：模型记不住上一句
    reply_no_ctx = client.chat(
        [{"role": "user", "content": "我刚才让你做什么了？"}]
    )
    print(f"[多轮·不带历史] {reply_no_ctx}\n")

    # 3) 多轮 —— 带历史：把上一轮的问答一起传回，模型才「记得」
    reply_with_ctx = client.chat(
        [
            {"role": "user", "content": "用一句话介绍你自己，并说明你能做什么。"},
            {"role": "assistant", "content": reply},
            {"role": "user", "content": "我刚才让你做什么了？"},
        ]
    )
    print(f"[多轮·带历史] {reply_with_ctx}\n")

    print("=== 阶段①完成：DeepSeek API 已跑通 ===")


if __name__ == "__main__":
    main()
