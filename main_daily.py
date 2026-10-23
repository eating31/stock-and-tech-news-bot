"""
main_daily.py
每日財經新聞主程式。
由 Cloud Scheduler 每天早上 07:00 (UTC+8) 觸發。

執行流程：
  1. 呼叫 OmniRouter → Perplexity sonar 取得今日財經新聞
  2. 格式化成 Line Bot 訊息
  3. 推播給所有指定對象
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# 本地開發時從 .env 載入環境變數
# GCP 部署時環境變數由 Cloud Run 注入，load_dotenv 不會覆蓋已存在的變數
load_dotenv(Path(__file__).parent / ".env")

from fetchers.news_fetcher import fetch_daily_news
from formatters.line_formatter import format_daily_news
from notifiers.line_notifier import send_message

# ── 日誌設定 ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run():
    logger.info("=== 每日財經新聞任務開始 ===")

    # Step 1：取得新聞資料
    try:
        news_data = fetch_daily_news()
    except Exception as e:
        logger.error(f"fetch_daily_news 發生未預期錯誤：{e}", exc_info=True)
        # 推播錯誤通知，讓你知道系統出問題
        send_message("⚠️ 每日財經新聞取得失敗，請檢查 OmniRouter 或 Perplexity API 狀態。")
        sys.exit(1)

    # Step 2：格式化訊息
    try:
        message = format_daily_news(news_data)
    except Exception as e:
        logger.error(f"format_daily_news 發生錯誤：{e}", exc_info=True)
        send_message("⚠️ 每日財經新聞格式化失敗，請檢查 formatter。")
        sys.exit(1)

    logger.info(f"訊息預覽（前 200 字）：\n{message[:200]}")

    # Step 3：推播
    success = send_message(message)
    if success:
        logger.info("=== 每日財經新聞任務完成 ===")
    else:
        logger.error("Line Bot 推播失敗")
        sys.exit(1)


if __name__ == "__main__":
    run()
