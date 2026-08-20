"""测试 FastAPI 接口（需先启动 uvicorn）。

用法：
    1. 先启动服务：uvicorn app.main:app --port 8000
    2. 再跑：python scripts/test_api.py
"""
import time

import requests

BASE = "http://127.0.0.1:8000"


def wait_server(retries: int = 20, delay: float = 0.5) -> None:
    for _ in range(retries):
        try:
            requests.get(f"{BASE}/docs", timeout=1)
            return
        except requests.exceptions.ConnectionError:
            time.sleep(delay)
    raise RuntimeError("服务未启动，请先运行 uvicorn app.main:app --port 8000")


def test_chat() -> None:
    print("=== /chat（普通接口，一次性返回）===")
    r = requests.post(f"{BASE}/chat", json={"message": "帮我算 6 * 7 等于多少？"})
    print("响应:", r.json())
    print()


def test_stream() -> None:
    print("=== /chat/stream（SSE 流式，逐 token 输出）===")
    with requests.post(
        f"{BASE}/chat/stream", json={"message": "公司年假有多少天？"}, stream=True
    ) as r:
        for line in r.iter_lines(decode_unicode=True):
            if line:
                print("  ", line)
    print()


if __name__ == "__main__":
    wait_server()
    test_chat()
    test_stream()
