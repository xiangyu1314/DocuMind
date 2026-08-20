"""知枢 (DocuMind) 全局配置。

所有配置统一从 .env 读取，代码里不硬编码密钥。
用法：
    from config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

设计说明：把「配置从哪来」集中在一处，换环境（本地/服务器）
或换 key 时只改 .env，不动代码。
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（本文件所在目录）
BASE_DIR = Path(__file__).resolve().parent

# 加载 .env；文件不存在则静默跳过（缺必需项会在 ensure_config 里报错）
load_dotenv(BASE_DIR / ".env")

# ---- DeepSeek 大模型 ----
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ---- MySQL（阶段② 查询工具 / 阶段⑤ 会话存储）----
MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "documind")

# ---- 阶段③ RAG 占位（用到时再启用）----
# QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")


def ensure_config() -> None:
    """启动时校验必需配置，缺失则抛出清晰报错（而非运行时才炸）。"""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError(
            "缺少 DEEPSEEK_API_KEY：请把 .env.example 复制为 .env，"
            "并填入你的 DeepSeek Key（https://platform.deepseek.com 获取）。"
        )
