"""阶段② 附加：MySQL 查询工具演示。

运行前先建表插数据：
    python scripts/setup_mysql.py
再运行本脚本：
    python scripts/phase2_mysql.py

观察点：知枢现在有两个工具（calculate / query_db），
它会自己判断「该不该查库、写什么 SQL」。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ensure_config

ensure_config()

from app.agent import run_agent


def main() -> None:
    print("=== 阶段② 附加：MySQL 查询工具 ===\n")

    questions = [
        "数据库里最贵的 3 个商品是什么？",
        "数码类商品一共有多少库存？",
        "哪些商品库存不足 10 个？",
    ]
    for q in questions:
        print(f"[用户] {q}")
        print(f"[知枢] {run_agent(q, verbose=True)}\n")

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
