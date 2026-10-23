"""
main_weekly.py
每週科技週報主程式。
由 Cloud Scheduler 每週一早上 08:00 (UTC+8) 觸發。

執行流程：
  1. 爬取 GitHub Trending（本週 top 15）
  2. 取得 Hacker News Top 10
  3. 呼叫 OmniRouter 產生本週 AI / 科技亮點摘要
  4. 整合格式化成 Line Bot 週報
  5. 推播給所有指定對象
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 本地開發時從 .env 載入環境變數
# GCP 部署時環境變數由 Cloud Run 注入，load_dotenv 不會覆蓋已存在的變數
load_dotenv(Path(__file__).parent / ".env")

from fetchers.github_trending import fetch_github_trending
from fetchers.hackernews import fetch_top_stories
from formatters.line_formatter import format_weekly_report, WEEKLY_DIGEST_PROMPT
from notifiers.line_notifier import send_message

# ── 日誌設定 ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── OmniRouter 設定 ───────────────────────────────────────
OMNI_BASE_URL  = os.environ.get("OMNI_BASE_URL", "http://omni-router:8080/v1")
OMNI_API_KEY   = os.environ.get("OMNI_API_KEY", "")
SEARCH_MODEL   = os.environ.get("SEARCH_MODEL", "perplexity/sonar")


def _build_weekly_digest(github_repos: list, hn_stories: list) -> str:
    """
    把 GitHub Trending + HN 資料餵給 OmniRouter，
    讓模型從這些原始資料裡整理成人讀的週報摘要。
    模型不需要搜尋網路，資料都在 prompt 裡。
    """
    # 格式化 GitHub 資料給 LLM
    github_text = "\n".join(
        f"{r['rank']}. {r['name']} ({r['language']}) — {r['description']} ⭐+{r['stars_week']}"
        for r in github_repos
    ) if github_repos else "（無資料）"

    # 格式化 HN 資料給 LLM
    hn_text = "\n".join(
        f"{s['rank']}. {s['title']} ({s['score']} pts)"
        for s in hn_stories
    ) if hn_stories else "（無資料）"

    prompt = WEEKLY_DIGEST_PROMPT.format(
        github_data=github_text,
        hn_data=hn_text,
    )

    try:
        client = OpenAI(base_url=OMNI_BASE_URL, api_key=OMNI_API_KEY)
        response = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你是科技週報編輯，用繁體中文輸出，語氣輕鬆易讀，適合一般讀者。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=1000,
        )
        digest = response.choices[0].message.content.strip()
        logger.info(f"[weekly_digest] 成功產生週報摘要（{len(digest)} 字）")
        return digest
    except Exception as e:
        logger.warning(f"[weekly_digest] 摘要產生失敗：{e}")
        return "⚠️ 本週 AI 摘要無法產生，請直接參考下方資料。"


def run():
    logger.info("=== 每週科技週報任務開始 ===")

    errors = []

    # Step 1：GitHub Trending
    try:
        github_repos = fetch_github_trending(limit=15)
    except Exception as e:
        logger.error(f"fetch_github_trending 失敗：{e}", exc_info=True)
        github_repos = []
        errors.append("GitHub Trending 取得失敗")

    # Step 2：Hacker News Top 10
    try:
        hn_stories = fetch_top_stories(limit=10)
    except Exception as e:
        logger.error(f"fetch_top_stories 失敗：{e}", exc_info=True)
        hn_stories = []
        errors.append("Hacker News 取得失敗")

    # Step 3：把原始資料餵給 LLM，整理成可讀週報摘要
    digest = _build_weekly_digest(github_repos, hn_stories)

    # Step 4：格式化
    try:
        message = format_weekly_report(digest)
    except Exception as e:
        logger.error(f"format_weekly_report 失敗：{e}", exc_info=True)
        send_message("⚠️ 科技週報格式化失敗，請檢查 formatter。")
        sys.exit(1)

    if errors:
        message += "\n\n⚠️ 部分資料取得失敗：" + "、".join(errors)

    logger.info(f"訊息預覽（前 200 字）：\n{message[:200]}")

    # Step 5：推播
    success = send_message(message)
    if success:
        logger.info("=== 每週科技週報任務完成 ===")
    else:
        logger.error("Line Bot 推播失敗")
        sys.exit(1)


if __name__ == "__main__":
    run()
