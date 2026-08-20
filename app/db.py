"""MySQL 访问封装（阶段② 查询工具 + 阶段⑤ 会话存储共用）。

统一在这里维护连接参数，工具层（tools.py）只管写 SQL、拿结果。
"""
import pymysql

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


def get_connection():
    """建立一条 MySQL 连接（调用方用完记得 close）。"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4",
        # Python 3.9 在 Windows 连 MySQL 读取系统证书库有已知 bug，需显式关掉
        ssl_disabled=True,
    )


def run_query(sql: str):
    """执行一条只读查询，返回 (列名列表, 行列表)。行是元组，与列名顺序一致。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
        return cols, rows
    finally:
        conn.close()
