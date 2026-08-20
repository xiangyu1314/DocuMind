"""多工具 Agent 演示：自动在「算数 / 查 MySQL / 查文档」三工具间路由。

运行前确保 MySQL 已初始化：
    python scripts/setup_mysql.py
（知识库会在脚本内自动重建并索引，无需单独跑 phase3）

运行：
    python scripts/agent_demo.py

观察点：同样一条 run_agent，模型面对不同问题会自动选不同工具。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ensure_config

ensure_config()

from app.agent import run_agent
from app.rag import index_document, reset_collection

DOC = Path(__file__).resolve().parents[1] / "data" / "考勤制度.md"


def main() -> None:
    print("=== 多工具 Agent 演示 ===\n")

    # 重建并索引知识库
    reset_collection()
    text = DOC.read_text(encoding="utf-8")
    n = index_document("考勤制度", text, source="data/考勤制度.md")
    print(f"[知识库] 已索引 {n} 个块\n")

    questions = [
        ("算数", "帮我算一下 (12 + 8) * 3 等于多少？"),
        ("查数据库", "数据库里最贵的商品是什么？"),
        ("查文档", "公司年假有多少天？"),
        ("查文档", "午休时间是几点到几点？"),
    ]
    for tag, q in questions:
        print(f"[用户] ({tag}) {q}")
        print(f"[知枢] {run_agent(q, verbose=True)}\n")

    print("=== 完成 ===")


if __name__ == "__main__":
    main()
