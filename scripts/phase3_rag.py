"""阶段③ 冒烟测试：RAG 检索问答 + 引用溯源。

运行（首次会下载 bge-small-zh-v1.5 模型，走 hf-mirror 镜像，需等一会）：
    python scripts/phase3_rag.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ensure_config

ensure_config()

from app.rag import index_document, rag_answer, reset_collection, retrieve

DOC = Path(__file__).resolve().parents[1] / "data" / "考勤制度.md"


def main() -> None:
    print("=== 阶段③：RAG 检索问答 ===\n")

    reset_collection()

    text = DOC.read_text(encoding="utf-8")
    print(f"[索引] 切块并向量化：{DOC.name}")
    n = index_document("考勤制度", text, source="data/考勤制度.md")
    print(f"[索引] 共写入 {n} 个块\n")

    # 先看检索效果：提问 -> 命中哪些块
    probe = "年假有多少天？"
    print(f"[检索] 问题：{probe}")
    for i, r in enumerate(retrieve(probe, top_k=3), 1):
        print(f"  命中{i} (score={r['score']:.3f}): {r['text'][:40].replace(chr(10), ' ')}...")
    print()

    # 再生成带引用的答案
    for q in ["年假有多少天？", "迟到几次以内不扣钱？", "午休时间是几点到几点？"]:
        print(f"[用户] {q}")
        print(f"[知枢] {rag_answer(q)}\n")

    print("=== 阶段③完成 ===")


if __name__ == "__main__":
    main()
