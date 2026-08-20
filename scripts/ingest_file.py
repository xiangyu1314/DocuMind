"""命令行文档入库（阶段⑤）。

用法：
    python scripts/ingest_file.py <文件路径> [更多文件...]

把一个或多个文档（.md/.txt/.docx/.pdf）解析并写入知识库，之后就能在对话里提问。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag import index_file


def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python scripts/ingest_file.py <文件路径> [更多文件...]")
        sys.exit(1)
    for path in sys.argv[1:]:
        n = index_file(path)
        print(f"✅ 已入库 {n} 个文本块：{path}")


if __name__ == "__main__":
    main()
