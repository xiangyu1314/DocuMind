"""Function Calling 工具集（阶段②③）。

这里分两块，对应「电话簿」和「屋里真正干活的」：

1. TOOLS        —— 工具描述（发给模型的"电话簿"）。模型只看到描述，
                   看不到你的实现，只能"喊"你调用。
2. TOOL_EXECUTORS —— 函数名 -> 实际函数。模型"喊"完之后，由你在这里
                   找到对应函数并真正执行。

关键：模型不会自己执行任何函数，执行权永远在你（调用方）手里。
"""
import ast
import json

from app.db import run_query


# ============ 1. 实际可执行的函数 ============

def calculate(expression: str) -> str:
    """安全计算一个四则运算表达式，返回结果字符串。"""
    # 用 ast 白名单解析，避免 eval 直接执行任意代码的风险
    _ALLOWED_NODES = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
        ast.USub, ast.UAdd,
    )
    try:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_NODES):
                raise ValueError("表达式包含不支持的运算")
        # 只允许纯算术：禁掉 __builtins__，不给任何名字空间
        result = eval(compile(tree, "<calc>", "eval"), {"__builtins__": {}}, {})
        return f"{result}"
    except Exception as e:  # noqa: BLE001
        return f"计算出错：{e}"


def query_db(sql: str) -> str:
    """只读查询 documind 数据库，返回结果文本。

    安全约束（本地演示级）：只允许 SELECT、拒绝分号（多语句注入）。
    生产级还应加：专用只读 MySQL 账号、连接池、查询超时。
    """
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned.lower().startswith("select"):
        return "只允许 SELECT 只读查询。"
    if ";" in cleaned:
        return "不允许分号（多语句）查询。"
    try:
        cols, rows = run_query(cleaned)
        if not cols:
            return "查询成功，但没有结果列。"
        lines = [", ".join(cols)]
        lines += [", ".join(str(v) for v in row) for row in rows]
        return f"共 {len(rows)} 行：\n" + "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        return f"查询出错：{e}"


def search_knowledge_base(query: str) -> str:
    """在本地知识库（Qdrant）中检索与 query 最相关的文档段落。

    懒导入 app.rag：只有真用到知识库工具时才加载 embedding 模型，
    纯算数 / 查库的场景不被拖慢。
    """
    from app.rag import retrieve

    results = retrieve(query, top_k=3)
    if not results:
        return "知识库为空或未检索到相关内容。"
    lines = []
    for i, r in enumerate(results, 1):
        src = r["source"] or "未知来源"
        lines.append(f"[资料{i}]（来源：{src}）{r['text']}")
    return "\n\n".join(lines)


# ============ 2. 工具注册表：函数名 -> 函数对象 ============

TOOL_EXECUTORS = {
    "calculate": calculate,
    "query_db": query_db,
    "search_knowledge_base": search_knowledge_base,
}


# ============ 3. 工具描述（发给模型的"电话簿"） ============

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "计算一个数学表达式，如 '(3 + 5) * 2'。"
                "当用户提出算术 / 计算类问题时调用此工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，例如 '3 + 5'",
                    },
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_db",
            "description": (
                "查询 documind 数据库中的商品表 products（列：id, name, category, price, stock）。"
                "当用户询问商品、价格、库存等需要查数据库的问题时，"
                "先根据问题写一条只读 SELECT 语句，再调用本工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": (
                            "要执行的只读 SELECT 语句，例如："
                            "SELECT * FROM products WHERE category = '数码'"
                        ),
                    },
                },
                "required": ["sql"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "在本地知识库中检索相关文档段落。"
                "当用户询问知识库、文档、公司制度、政策等内容时调用；"
                "检索到的段落可作为回答依据。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索关键词或问题，例如 '年假有多少天'",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# ============ 4. 执行入口：模型喊 -> 这里动手 ============

def execute_tool(name: str, arguments: str) -> str:
    """根据模型返回的工具名 + JSON 参数字符串，真正执行对应函数。"""
    func = TOOL_EXECUTORS.get(name)
    if func is None:
        return f"未知工具：{name}"
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return f"参数不是合法 JSON：{arguments}"
    return str(func(**args))
