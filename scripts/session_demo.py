"""会话管理演示（阶段⑤）：多轮历史持久化到 MySQL。

演示「刷新 / 重启不丢历史」这件事为什么重要：第二句话只说「那再加 5 呢」，
没有历史就答不上来；从 MySQL 读回历史喂给 Agent 后就能接着上下文算对。

运行前确保 MySQL 已初始化：
    python scripts/setup_mysql.py

运行：
    python scripts/session_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ensure_config

ensure_config()

from app.agent import run_agent
from app.session_store import (
    add_message,
    create_session,
    delete_session,
    get_messages,
    list_sessions,
)


def main() -> None:
    print("=== 会话管理演示（多轮历史持久化）===\n")

    # 1) 新建一个会话
    sid = create_session("多轮算术演示")
    print(f"[新建会话] session_id = {sid}\n")

    # 2) 第一轮：正常提问
    q1 = "帮我算 20 + 21 等于多少？"
    add_message(sid, "user", q1)
    a1 = run_agent(q1, history=get_messages(sid)[:-1])  # 历史不含本条 user
    add_message(sid, "assistant", a1)
    print(f"[第1轮 用户] {q1}")
    print(f"[第1轮 知枢] {a1}\n")

    # 3) 第二轮：只靠上下文（没历史就答不上来）
    q2 = "那再加 5 呢？"
    prior = get_messages(sid)  # 此时含第1轮的 user+assistant
    add_message(sid, "user", q2)
    a2 = run_agent(q2, history=prior)
    add_message(sid, "assistant", a2)
    print(f"[第2轮 用户] {q2}")
    print(f"[第2轮 知枢] {a2}")
    print("   ↑ 正确答案应是 46，说明历史已正确喂回上下文\n")

    # 4) 模拟「刷新页面」：重新从 MySQL 读回完整历史
    msgs = get_messages(sid)
    print(f"[重新加载] 该会话共 {len(msgs)} 条消息：")
    for m in msgs:
        print(f"    {m['role']:9s} {m['content'][:40]}")
    print()

    # 5) 会话列表 + 清理
    print(f"[会话列表] 当前共 {len(list_sessions())} 个会话")
    delete_session(sid)
    print(f"[清理] 已删除演示会话 {sid}，剩余 {len(list_sessions())} 个会话")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()
