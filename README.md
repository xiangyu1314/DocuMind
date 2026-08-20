# 知枢 (DocuMind)

本地知识库智能问答 Agent —— **手写** RAG + Function Calling，不依赖 LangChain / LlamaIndex / Dify。

> 定位：够分量上简历的项目。核心逻辑自己实现，简历上写的是「会做」而非「会用」。

## 技术栈

| 层 | 选型 |
| --- | --- |
| 大模型 | DeepSeek（`deepseek-chat`，OpenAI 兼容接口） |
| LLM SDK | `openai`（万能遥控器，一套 SDK 调多家） |
| 后端 | FastAPI（SSE 流式输出） |
| 向量库 | Qdrant（本地 Docker） |
| 会话存储 | MySQL（历史 + 会话管理） |
| 前端 | Gradio |

## 路线图

- [x] 阶段① 跑通 DeepSeek API（多轮 / system prompt）
- [x] 阶段② Function Calling 工具调用（算数 `calculate` + 查 MySQL `query_db`，手写 ReAct 循环）
- [x] 阶段③ RAG（切块 → embedding → Qdrant 检索 → 引用溯源）
- [x] 阶段④ 合成 FastAPI 项目（SSE 流式）
- [ ] 阶段⑤ 增值功能（多格式解析 / 会话管理 / Gradio 前端）

## 快速开始

```bash
conda activate NLP
cd D:\NLPCode\DocuMind

# 1. 配置密钥
copy .env.example .env        # 然后编辑 .env，填入 DEEPSEEK_API_KEY

# 2. 阶段① 冒烟测试
python scripts/phase1_smoke.py

# 3. 启动 FastAPI 服务（阶段④）
python -m uvicorn app.main:app --port 8000
# 浏览器打开 http://127.0.0.1:8000/docs 看接口文档
```

## 目录结构

```
DocuMind/
├── config.py            # 全局配置（读 .env）
├── app/
│   ├── llm.py           # DeepSeek 客户端封装
│   └── ...              # 阶段②-⑤ 逐步加入
├── scripts/             # 各阶段冒烟/测试脚本
├── data/                # 知识库文档（阶段③测试用）
├── .env.example         # 环境变量模板
└── requirements.txt
```
