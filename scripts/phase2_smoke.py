"""阶段② 冒烟测试：function calling 工具调用。

运行：
    conda activate NLP
    python scripts/phase2_smoke.py

会演示两问：
1. 需要算数 -> 模型"喊" calculate 工具 -> 我们执行 -> 模型拿结果组织答案；
2. 不需要工具 -> 模型直接回答，不喊工具。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ensure_config

ensure_config()

from app.agent import run_agent


def main() -> None:
    print("=== 阶段②：Function Calling 工具调用 ===\n")

    q1 = "帮我算一下 (3 + 5) * 7 等于多少？"
    print(f"[用户] {q1}")
    print(f"[知枢] {run_agent(q1, verbose=True)}\n")

    q2 = "用一句话介绍你自己。"
    print(f"[用户] {q2}")
    print(f"[知枢] {run_agent(q2, verbose=True)}\n")

    print("=== 阶段②完成 ===")


if __name__ == "__main__":
    main()
