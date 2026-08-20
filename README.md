# 知枢 (DocuMind)

本地知识库智能问答 Agent —— **手写** RAG + Function Calling + 会话管理，不依赖 LangChain / LlamaIndex / Dify 等框架。

> 定位：够分量上简历的项目。核心逻辑（工具调用循环、切块检索、会话持久化）全部自己实现，简历上写的是「会做」而非「会用」。

---

## ✨ 一句话看懂它

用户用自然语言提问，Agent 自动判断「该不该查库 / 查文档 / 算数」，调用工具拿到结果后回答；所有对话历史持久化到 MySQL，刷新页面不丢。

```
你问：公司年假有多少天？
  └─ 模型判断 → 该查文档 → search_knowledge_base("年假") → 检索 Qdrant → 带引用回答

你问：数据库里最贵的商品是什么？
  └─ 模型判断 → 该查库 → query_db("SELECT ... ORDER BY price DESC LIMIT 1") → 回答

你问：(12 + 8) * 3 等于多少？
  └─ 模型判断 → 该算数 → calculate("(12 + 8) * 3") → 60
```

---

## 🎯 核心亮点

| 亮点 | 说明 |
| --- | --- |
| **手写 ReAct 循环** | 不用框架的 agent 循环，自己实现「模型喊工具 → 执行 → 喂回结果 → 再判断」的多轮对讲 |
| **Function Calling 三工具** | `calculate`（AST 白名单安全算术）、`query_db`（SELECT 只读 + 防注入）、`search_knowledge_base`（RAG 检索） |
| **手写 RAG** | 标题切段 → 句边界切块 → 本地 bge 向量化 → Qdrant 检索 → 带引用生成 |
| **多格式解析** | 用「魔法字节」嗅探真实文件类型，.md/.txt/.docx/.pdf 统一抽文本（docx 含表格） |
| **会话管理** | MySQL 存会话 + 消息，FastAPI REST + Gradio 界面均支持多轮持久化 |
| **流式输出** | SSE 逐 token 输出，工具调用过程的「思考」文本不泄露给用户 |

---

## 🧱 架构

```
                    ┌─────────────────────────────────────────┐
                    │              接入层（两个入口）              │
                    │   Gradio 界面（可视化）  /  FastAPI（REST） │
                    └───────────────┬─────────────────────────┘
                                    │ run_agent / run_agent_stream
                    ┌───────────────▼─────────────────────────┐
                    │        Agent 核心（手写 ReAct 循环）        │
                    │   判断：直接回答  or  调用哪个工具？           │
                    └───┬───────────┬───────────┬─────────────┘
                        │           │           │
                 ┌──────▼───┐ ┌─────▼─────┐ ┌───▼────────────┐
                 │ calculate │ │ query_db  │ │ search_knowledge_base
                 │ (AST白名单)│ │ (SELECT)  │ │   └─ RAG 流水线
                 └───────────┘ └─────┬─────┘ └───┬────────────┘
                                     │           │
                              ┌──────▼───┐  ┌────▼───────────┐
                              │  MySQL    │  │ Qdrant（本地嵌入）│
                              │ products  │  │ + bge 向量模型  │
                              │ sessions  │  └────────────────┘
                              │ messages  │
                              └──────────┘
```

---

## 🛠 技术栈

| 层 | 选型 | 说明 |
| --- | --- | --- |
| 大模型 | DeepSeek（`deepseek-chat`） | OpenAI 兼容接口，`openai` SDK 直连 |
| 后端 | FastAPI + uvicorn | SSE 流式输出 |
| 前端 | Gradio | 会话管理 + 文档入库两个页签 |
| 向量库 | Qdrant（**本地嵌入模式**） | 文件存储，无需 Docker；上服务器版只需把 `path=` 换成 `url=` |
| 向量模型 | `BAAI/bge-small-zh-v1.5` | 本地 sentence-transformers，离线免费 |
| 会话存储 | MySQL 8.x | sessions + messages 两表，外键级联删除 |
| 文档解析 | python-docx / pdfplumber | docx 正文+表格、PDF 逐页抽文本 |

---

## 🚀 快速开始

### 0. 环境准备

```bash
conda activate NLP                    # Python 3.9 环境
pip install -r requirements.txt       # 依赖见 requirements.txt
```

### 1. 配置密钥

```bash
copy .env.example .env                # 复制模板
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 MYSQL_PASSWORD
```

### 2. 初始化 MySQL（建表 + 演示数据）

```bash
python scripts/setup_mysql.py
```

### 3. 三种方式体验

**A. 命令行多工具演示**（最快看到效果，自动在算数/查库/查文档间路由）：

```bash
python scripts/agent_demo.py
```

**B. Gradio 可视化界面**（推荐，含会话管理）：

```bash
python app/gradio_app.py
# 浏览器打开 http://127.0.0.1:7860
```

**C. FastAPI 接口**（SSE 流式）：

```bash
python -m uvicorn app.main:app --port 8000
# 接口文档 http://127.0.0.1:8000/docs
# 测试脚本 python scripts/test_api.py
```

### 4. 文档入库

```bash
python scripts/ingest_file.py data/考勤制度.md      # 也支持 .txt/.docx/.pdf
# 或在 Gradio 的「文档入库」页输入文件绝对路径
```

---

## 📁 项目结构

```
DocuMind/
├── config.py              # 全局配置（统一从 .env 读取）
├── app/
│   ├── llm.py             # DeepSeek 客户端封装（complete/chat/stream）
│   ├── agent.py           # ★ Agent 核心：手写 ReAct 循环 + 流式版
│   ├── tools.py           # ★ 工具集：calculate / query_db / search_knowledge_base
│   ├── db.py              # MySQL 连接封装
│   ├── session_store.py   # 会话 + 消息 CRUD（阶段⑤）
│   ├── embedder.py        # 向量化封装（本地 bge 模型）
│   ├── rag.py             # ★ RAG：切块/向量化/入库/检索/带引用生成
│   ├── parser.py          # 多格式解析（魔法字节嗅探 .md/.txt/.docx/.pdf）
│   ├── main.py            # FastAPI 服务（REST + SSE）
│   └── gradio_app.py      # Gradio 前端（会话管理 + 文档入库）
├── scripts/
│   ├── agent_demo.py      # 多工具端到端演示（推荐先跑这个）
│   ├── setup_mysql.py     # 建库建表 + 演示数据
│   ├── ingest_file.py     # 命令行文档入库
│   ├── test_api.py        # FastAPI 接口测试
│   └── phase*.py          # 各阶段冒烟测试
├── data/                  # 知识库文档（演示用）
├── .env.example           # 环境变量模板（.env 已被 gitignore）
└── requirements.txt
```

---

## 🧩 核心模块说明

### Agent 循环（`app/agent.py`）

整个项目的灵魂。模型不会执行工具，它只会「喊」要调哪个、传什么参数；执行权始终在我们手里：

```
用户提问 → [模型：要不要调工具？]
   ├─ 不调 → 直接返回答案
   └─ 调   → 执行工具 → 结果以 role="tool" 喂回 → 再问模型 → …（最多 5 轮）
```

- `run_agent`：一次性返回完整答案（`verbose=True` 可看工具调用细节）
- `run_agent_stream`：逐 token 流式输出；工具调用轮的「思考」文本先缓冲、有工具调用则丢弃，不泄露给用户

### RAG 流水线（`app/rag.py`）

```
文档 → 魔法字节嗅探类型 → 抽文本 → 标题切段 → 句边界切块(overlap) → bge 向量化 → Qdrant
提问 → 向量化(带 query 前缀) → Qdrant top_k 检索 → 拼【资料】→ 模型带引用回答
```

### 安全设计（本地演示级）

| 工具 | 防护 |
| --- | --- |
| `calculate` | `ast` 白名单节点 + 空 `__builtins__`，杜绝任意代码执行 |
| `query_db` | 只允许 `SELECT`、拒绝分号多语句注入 |
| `search_knowledge_base` | 懒导入，非文档场景不加载 embedding 模型 |

---

## 📝 踩坑记录（工程能力的一部分）

- **gradio 4.44.1 强制依赖 gradio_client==1.3.0**（Python 3.9 升不了 gradio 5）：组件「同时作为事件输入+输出」时（如 Chatbot 边收历史边流式回写），生成的 schema 带 `additionalProperties: true`，`get_api_info()` 里 `"const" in True` 崩。修复：monkey-patch 补布尔分支。
- **embedding 离线加载**：gradio 在 import 时连带 import huggingface_hub 固化了 `HF_ENDPOINT`，必须在 `import gradio` 前设镜像 + 离线开关。
- **DeepSeek 流式 + 工具**：喊工具前会先吐一句「思考」，需缓冲并丢弃，否则泄露给用户。
- **Qdrant 本地模式是单进程锁**：测试时需先停掉正在跑的 gradio 进程，否则报「已锁」。

---

## 📌 展望

- [ ] RAG 检索增强：混合检索（关键词 + 向量）、重排序
- [ ] 多用户鉴权（当前本地单用户）
- [ ] 部署上线（Qdrant 切服务器模式、uvicorn 生产配置）
- [ ] 更多数据源（数据库 schema 自动生成工具描述，而非硬编码 products 表）

---

## 📄 许可

个人学习 / 求职项目，暂不设开源协议。
