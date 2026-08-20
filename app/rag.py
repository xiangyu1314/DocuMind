"""RAG 核心（阶段③）：切块 -> 向量化 -> 入库 -> 检索 -> 带引用生成。

「开卷考试的小抄」流水线。Qdrant 用本地嵌入模式（文件存储，无需 Docker），
以后要上服务器版只需把 get_client 里的 path= 换成 url=http://localhost:6333。
"""
import atexit
import re
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.embedder import dim, embed_documents, embed_query
from app.llm import client as llm

COLLECTION = "documind_chunks"
CHUNK_SIZE = 300       # 每块最多字符数
CHUNK_OVERLAP = 50     # 相邻块重叠字符数（避免一句话被从中间切断）

_client = None


def get_client() -> QdrantClient:
    """懒加载单例。本地嵌入模式，数据落到项目下 qdrant_data 目录。"""
    global _client
    if _client is None:
        root = Path(__file__).resolve().parents[1]
        _client = QdrantClient(path=str(root / "qdrant_data"))
        atexit.register(_client.close)  # 进程退出前显式关闭，避免 portalocker 告警
    return _client


def ensure_collection() -> None:
    """集合不存在则创建（向量维度由模型决定，距离用余弦）。"""
    client = get_client()
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim(), distance=Distance.COSINE),
        )


def reset_collection() -> None:
    """清空并重建集合（保证演示脚本可重复运行，不累积旧数据）。"""
    get_client().recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=dim(), distance=Distance.COSINE),
    )


def split_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """先按 Markdown 标题切段，再在段内按句子边界切块，块间留 overlap。

    这样每个「## 章节」自成一体，标题和正文不散开，也不会和相邻章节混在一
    块里 —— 检索时命中的块语义更完整（chunking 质量决定检索质量）。
    """
    # 1) 按标题切段：在下一个 `#` 标题行之前断开（标题跟随其内容）
    sections = re.split(r"(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    chunks: list[str] = []
    for section in sections:
        # 2) 段内按句子边界切块
        sentences = re.split(r"(?<=[。！？!?；;\n])", section)
        sentences = [s for s in sentences if s.strip()]
        cur = ""
        for s in sentences:
            if len(cur) + len(s) > size and cur:
                chunks.append(cur)
                cur = cur[-overlap:] if overlap else ""
            cur += s
        if cur.strip():
            chunks.append(cur)
    return chunks


def index_document(doc_id: str, text: str, source: str = "") -> int:
    """切块 -> 向量化 -> 写入 Qdrant，返回写入的块数。"""
    ensure_collection()
    chunks = split_chunks(text)
    if not chunks:
        return 0
    vectors = embed_documents(chunks)

    client = get_client()
    # 从当前已有点数继续编号，保证多次入库 id 不冲突
    base = client.count(collection_name=COLLECTION, exact=True).count
    points = [
        PointStruct(
            id=base + i,
            vector=vec,
            payload={
                "doc_id": doc_id,
                "source": source,
                "chunk_idx": i,
                "text": chunk,
            },
        )
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    client.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def index_file(path) -> int:
    """解析任意支持格式的文件并入库（解析 -> 切块 -> 向量化 -> 写入），返回块数。

    与 index_document 的区别：index_document 吃「纯文本」，这里吃「文件路径」，
    内部先调 app.parser.parse_file 把 .md/.txt/.docx/.pdf 抽成文本。
    """
    from app.parser import parse_file  # 懒导入：不传文件的场景不加载解析库

    p = Path(path)
    text = parse_file(p)
    if not text.strip():
        return 0
    return index_document(doc_id=p.stem, text=text, source=p.name)


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """提问 -> 向量化 -> Qdrant 检索最相似的 top_k 块。"""
    ensure_collection()
    qvec = embed_query(query)
    resp = get_client().query_points(collection_name=COLLECTION, query=qvec, limit=top_k)
    return [
        {
            "score": h.score,
            "text": h.payload["text"],
            "source": h.payload.get("source", ""),
            "chunk_idx": h.payload.get("chunk_idx", 0),
        }
        for h in resp.points
    ]


RAG_SYSTEM_PROMPT = (
    "你是知枢。请只根据下面提供的【资料】回答用户问题，"
    "并在答案中标注引用的资料编号（如 [资料1]）。"
    "如果资料中没有答案，请明确回答「资料中未提及」，不要编造。"
)


def rag_answer(question: str, top_k: int = 3) -> str:
    """RAG 问答：检索 -> 拼资料 -> 让模型带引用回答。"""
    contexts = retrieve(question, top_k=top_k)
    blocks = "\n\n".join(f"[资料{i + 1}] {c['text']}" for i, c in enumerate(contexts))

    messages = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
        {"role": "user", "content": f"【资料】\n{blocks}\n\n【问题】{question}"},
    ]
    return llm.chat(messages)
