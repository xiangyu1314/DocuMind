"""生成 README 演示截图（开发用，不进 requirements）。

用 Playwright 驱动本机 Edge，真实打开 Gradio 界面、输入问题、等回答、截图。
用法：
    python scripts/capture_screenshot.py [问题] [输出路径]

默认问题「公司年假有多少天？」（展示 RAG 检索 + 带引用回答）。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:7860"
QUESTION = sys.argv[1] if len(sys.argv) > 1 else "公司年假有多少天？"
OUT = sys.argv[2] if len(sys.argv) > 2 else str(
    Path(__file__).resolve().parents[1] / "assets" / "screenshot.png"
)


def main() -> None:
    with sync_playwright() as p:
        # 用系统自带 Edge（channel="msedge"），无需额外下载浏览器
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1000})

        page.goto(URL, wait_until="domcontentloaded")
        # Gradio 前端有长连接，networkidle 永远等不到，改等关键元素出现
        page.wait_for_selector("textarea", timeout=20000)

        # 输入问题并回车（Gradio Textbox 回车即提交）
        box = page.locator("textarea").first
        box.fill(QUESTION)
        box.press("Enter")

        # 等回答：聊天区出现回复气泡（.message 是 gradio 聊天气泡的类名）
        page.wait_for_selector(".message.bot, .message.user", timeout=30000)
        # 再等流式输出完整吐出
        page.wait_for_timeout(12000)

        page.screenshot(path=OUT, full_page=False)
        print(f"✅ 截图已保存：{OUT}")
        browser.close()


if __name__ == "__main__":
    main()
