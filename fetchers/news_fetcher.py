"""
news_fetcher.py
兩階段取得每日財經新聞：
  Step 1. NewsAPI（免費）→ 取得今日財經相關原始文章
  Step 2. OmniRouter → GPT-4o → 整理成結構化 JSON + 台灣大盤影響分析

不需要 Perplexity，完全使用你現有的 GitHub Copilot API。
"""

import os
import json
import re
import logging
from datetime import date, timedelta
from openai import OpenAI
import requests

logger = logging.getLogger(__name__)

# ── NewsAPI 設定 ──────────────────────────────────────────
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# 財經關鍵字：直接影響台股的優先，次要的補後面
NEWS_KEYWORDS = (
    "TSMC OR \"Taiwan Semiconductor\" OR "
    "Fed OR \"Federal Reserve\" OR \"interest rate\" OR \"rate cut\" OR \"rate hike\" OR "
    "\"US CPI\" OR \"US inflation\" OR \"US GDP\" OR \"nonfarm payrolls\" OR "
    "NASDAQ OR \"S&P 500\" OR "
    "\"China economy\" OR \"China PMI\" OR "
    "KOSPI OR Samsung OR \"SK Hynix\" OR "
    "\"US China trade\" OR tariff OR "
    "\"oil price\" OR \"crude oil\""
)

# ── OmniRouter 設定 ───────────────────────────────────────
OMNI_BASE_URL = os.environ.get("OMNI_BASE_URL", "http://omni-router:8080/v1")
OMNI_API_KEY  = os.environ.get("OMNI_API_KEY", "")
SEARCH_MODEL  = os.environ.get("SEARCH_MODEL", "gpt-4o")

# ── Prompt ────────────────────────────────────────────────
SUMMARIZE_PROMPT = """你是專業的台灣股市分析師助理，每天產生固定格式的財經情報。

以下是今天（{today}）的財經新聞原文，請依照規則整理後輸出 JSON。

新聞資料：
{articles}

**整理規則：**
1. 從新聞中挑選 5～7 條，優先順序：直接影響台股 > 美股科技/半導體 > 總體經濟數據 > 其他
2. market_sentiment 判斷標準：
   - 偏多：正面消息 >= 負面消息 × 1.5，且主要指數預期上漲
   - 偏空：負面消息 >= 正面消息 × 1.5，且主要指數預期下跌
   - 中性：其餘情況
3. finance_concept 選今日新聞中出現頻率最高或最關鍵的那一個概念，優先選一般讀者不熟悉的詞

**輸出格式（只回傳 JSON，禁止在 JSON 前後加任何文字）：**
{{
  "date": "{today}",
  "market_sentiment": "偏多 | 偏空 | 中性",
  "summary": "今日整體市場氣氛總結，40字以內，結尾說明對台股的預期方向",
  "finance_concept": {{
    "term": "一個金融名詞（繁體中文，6字以內）",
    "explanation": "這個詞是什麼意思，以及為何牽動台股，50字以內，白話文，不用專業術語"
  }},
  "news": [
    {{
      "title": "繁體中文標題，25字以內",
      "source": "媒體名稱",
      "summary": "發生了什麼事，25字以內",
      "impact": "正面 | 負面 | 中性",
      "impact_reason": "為何影響台灣大盤，15字以內"
    }}
  ]
}}"""


def _fetch_from_newsapi(today: str) -> list[dict]:
    """
    呼叫 NewsAPI 取得今日財經相關文章。
    回傳原始文章列表，每筆包含 title、description、source、publishedAt、url。
    """
    if not NEWS_API_KEY:
        raise ValueError("NEWS_API_KEY 未設定，請在 .env 填入 NewsAPI key（newsapi.org 免費申請）")

    # 搜尋今天和昨天的新聞（避免時區差異造成空結果）
    yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()

    params = {
        "q": NEWS_KEYWORDS,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 30,           # 多抓一些，讓 LLM 有得選
        "from": yesterday,
        "to": today,
        "apiKey": NEWS_API_KEY,
    }

    logger.info(f"[news_fetcher] 呼叫 NewsAPI，日期範圍：{yesterday} ~ {today}")

    resp = requests.get(NEWS_API_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"NewsAPI 回傳錯誤：{data.get('message', '未知錯誤')}")

    articles = data.get("articles", [])
    logger.info(f"[news_fetcher] NewsAPI 取得 {len(articles)} 篇文章")

    # 只保留需要的欄位，節省 token
    return [
        {
            "title": a.get("title", ""),
            "description": a.get("description", "") or "",
            "source": a.get("source", {}).get("name", ""),
            "publishedAt": a.get("publishedAt", "")[:10],  # 只留日期
        }
        for a in articles
        if a.get("title") and "[Removed]" not in a.get("title", "")
    ]


def _summarize_with_llm(articles: list[dict], today: str) -> dict:
    """
    將 NewsAPI 文章列表餵給 OmniRouter（GPT-4o），
    輸出結構化 JSON（market_sentiment、summary、news 列表）。
    """
    # 格式化文章列表給 LLM，每篇一行
    articles_text = "\n".join(
        f"[{i+1}] {a['source']} | {a['publishedAt']} | {a['title']}。{a['description']}"
        for i, a in enumerate(articles)
    )

    prompt = SUMMARIZE_PROMPT.format(today=today, articles=articles_text)

    client = OpenAI(base_url=OMNI_BASE_URL, api_key=OMNI_API_KEY)

    logger.info(f"[news_fetcher] 呼叫 OmniRouter（{SEARCH_MODEL}）整理 {len(articles)} 篇文章")

    response = client.chat.completions.create(
        model=SEARCH_MODEL,
        messages=[
            {
                "role": "system",
                "content": "你是專業財經分析師，只輸出符合規格的 JSON，不附加任何說明文字。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=3000,
    )

    raw = response.choices[0].message.content.strip()

    # 清除 LLM 有時會加的 ```json ... ``` 包裹
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # 清除 trailing comma（部分模型會產生不合法的 JSON）
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        result = json.loads(raw)
        logger.info(f"[news_fetcher] 成功整理出 {len(result.get('news', []))} 條新聞")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"[news_fetcher] JSON 解析失敗：{e}\n原始內容：{raw[:300]}")
        return {"date": today, "raw_error": raw, "news": []}


def fetch_daily_news() -> dict:
    """
    主要對外介面。
    Step 1: NewsAPI 取原始文章
    Step 2: OmniRouter GPT-4o 整理分析
    回傳結構化 dict，schema 見 SUMMARIZE_PROMPT。
    """
    today = date.today().strftime("%Y-%m-%d")
    logger.info(f"[news_fetcher] 開始取得 {today} 財經新聞")

    articles = _fetch_from_newsapi(today)

    if not articles:
        logger.warning("[news_fetcher] NewsAPI 未取得任何文章，回傳空結果")
        return {"date": today, "market_sentiment": "中性", "summary": "今日無法取得新聞資料", "news": []}

    return _summarize_with_llm(articles, today)
