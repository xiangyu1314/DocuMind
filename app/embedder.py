"""向量化封装（阶段③ RAG）：本地 sentence-transformers + bge-small-zh。

embedding = 把文字变成一串数字（向量），语义相近的文字向量距离近。
用本地模型的好处：免费、离线、不用再开任何 key。首次加载会自动下载模型。
"""
import os

# 国内从 HuggingFace 下载慢/被墙，走镜像（只在下载时生效，加载本地缓存则无影响）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from sentence_transformers import SentenceTransformer  # noqa: E402

MODEL_NAME = "BAAI/bge-small-zh-v1.5"  # 中文检索常用小模型，向量维度 512

# bge 系列官方推荐：检索时给 query 加这个前缀，能明显提升检索质量。
# 注意：只有「查询」加前缀，「文档」不加。
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："

_model = None


def get_model() -> SentenceTransformer:
    """懒加载单例：首次调用才下载/加载模型，后续复用。"""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_documents(texts: list[str]) -> list[list[float]]:
    """把「文档段落」向量化（不带 query 前缀）。"""
    return get_model().encode(texts, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    """把「用户提问」向量化（带 query 前缀）。"""
    return get_model().encode(QUERY_INSTRUCTION + text, normalize_embeddings=True).tolist()


def dim() -> int:
    """返回向量维度（创建 Qdrant collection 时需要）。"""
    return get_model().get_sentence_embedding_dimension()
