"""
line_formatter.py
將各 fetcher 的原始資料轉換成 Line Bot 訊息格式。
"""

from datetime import date
from typing import List


IMPACT_EMOJI = {
    "正面": "🟢",
    "負面": "🔴",
    "中性": "🟡",
}

SENTIMENT_EMOJI = {
    "偏多": "📈",
    "偏空": "📉",
    "中性": "➡️",
}


# ── 每日財經新聞格式 ──────────────────────────────────────
def format_daily_news(data: dict) -> str:
    today = data.get("date", date.today().strftime("%Y-%m-%d"))
    sentiment = data.get("market_sentiment", "中性")
    summary = data.get("summary", "")
    news_list: List[dict] = data.get("news", [])
    concept = data.get("finance_concept", {})

    sentiment_icon = SENTIMENT_EMOJI.get(sentiment, "➡️")

    lines = [
        f"📰 每日財經情報｜{today}",
        f"{'─' * 22}",
        f"{sentiment_icon} 今日大盤氣氛：{sentiment}",
        f"💬 {summary}",
        "",
    ]

    if not news_list:
        lines.append("⚠️ 今日無法取得新聞資料，請稍後再試。")
        return "\n".join(lines)

    for i, item in enumerate(news_list, start=1):
        impact = item.get("impact", "中性")
        icon = IMPACT_EMOJI.get(impact, "🟡")
        title = item.get("title", "（無標題）")
        source = item.get("source", "")
        summary_line = item.get("summary", "")
        reason = item.get("impact_reason", "")

        lines.append(f"{i}. {icon} {title}")
        if source:
            lines.append(f"   📌 {source}")
        lines.append(f"   {summary_line}")
        if reason:
            lines.append(f"   → 台灣影響：{reason}")
        lines.append("")

    # ── 今日金融小概念 ──
    if concept and concept.get("term") and concept.get("explanation"):
        lines.append("─" * 22)
        lines.append(f"📖 今日概念：{concept['term']}")
        lines.append(f"   {concept['explanation']}")
        lines.append("")

    lines.append("─" * 22)
    lines.append("🤖 由 AI 自動整理，僅供參考，不構成投資建議")

    return "\n".join(lines)


# ── 每週科技週報格式（只顯示 LLM 整理後的摘要）──────────
def format_weekly_report(digest: str) -> str:
    """
    接收 LLM 整理好的週報全文（純文字），加上 header/footer 後輸出。
    不再直接顯示原始清單。
    """
    today = date.today().strftime("%Y-%m-%d")

    lines = [
        f"🚀 科技週報｜{today}",
        f"{'─' * 22}",
        "",
        digest.strip(),
        "",
        "─" * 22,
        "🤖 由 AI 整理｜資料來源：GitHub Trending / Hacker News",
    ]

    return "\n".join(lines)


# ── 週報整理 prompt（給 main_weekly 用）─────────────────
WEEKLY_DIGEST_PROMPT = """你是科技週報編輯，請根據以下原始資料整理週報，每次輸出結構固定。

## GitHub Trending 本週熱門（前15名）
{github_data}

## Hacker News 熱門討論（前10名）
{hn_data}

**整理規則：**
- 優先選與 AI、開發工具、資安、開源有關的項目
- 排除與台灣無關且話題性低的一般娛樂或生活類內容
- 不要列連結、分數、留言數

**輸出兩個固定區塊，直接輸出內容，不要任何前言：**

【🔥 本週科技亮點】
從資料中挑出剛好 4 點值得關注的趨勢或事件，每點格式：
• 主題標題（粗體）：1～2 句說明是什麼、為什麼值得關注

【⭐ 本週 GitHub 精選】
從 GitHub Trending 挑出剛好 4 個專案，每個格式：
• 專案名稱：一句話說明它是什麼、能解決什麼問題"""
