"""会话管理（阶段⑤）：把多轮对话历史持久化到 MySQL。

作用：刷新页面 / 重启服务后历史还在；也能列出、切换、删除会话。
表结构见 scripts/setup_mysql.py（sessions + messages 两张表，外键级联删除）。
"""
from app.db import get_connection


def create_session(title: str = "新会话") -> int:
    """新建会话，返回 session_id。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO sessions (title) VALUES (%s)", (title,))
            sid = cur.lastrowid
        conn.commit()
        return sid
    finally:
        conn.close()


def list_sessions(limit: int = 50) -> list[dict]:
    """按最近更新倒序列出会话。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at, updated_at "
                "FROM sessions ORDER BY updated_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {"id": r[0], "title": r[1], "created_at": str(r[2]), "updated_at": str(r[3])}
            for r in rows
        ]
    finally:
        conn.close()


def get_messages(session_id: int) -> list[dict]:
    """取某会话全部消息（按时间正序），返回 OpenAI 风格 [{role, content}, ...]。

    正好能直接喂给 run_agent(history=...) 做多轮上下文。
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role, content FROM messages WHERE session_id=%s ORDER BY id ASC",
                (session_id,),
            )
            rows = cur.fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]
    finally:
        conn.close()


def add_message(session_id: int, role: str, content: str) -> None:
    """追加一条消息，并刷新会话的 updated_at（让列表排序更准确）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
                (session_id, role, content),
            )
            cur.execute("UPDATE sessions SET updated_at=NOW() WHERE id=%s", (session_id,))
        conn.commit()
    finally:
        conn.close()


def delete_session(session_id: int) -> None:
    """删除会话；其消息由外键 ON DELETE CASCADE 一并删除。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id=%s", (session_id,))
        conn.commit()
    finally:
        conn.close()
