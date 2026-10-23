"""
test_local.py
階段性本地測試腳本，不需要 Docker。
用法：python test_local.py [stage]

stage 選項：
  1  測試 OmniRouter 連線
  2  測試 NewsAPI 抓新聞原文
  3  測試完整財經新聞流程（NewsAPI + LLM 整理）
  4  測試 GitHub Trending 爬蟲
  5  測試 Hacker News API
  6  測試 Line Bot 推播（會真的發訊息給你）
  all  跑所有階段（6 除外，避免一直收到測試訊息）

範例：
  python test_local.py 1
  python test_local.py 3
  python test_local.py 6
  python test_local.py all
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env（確保從 news-digest 目錄找）
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"✅ 載入 .env：{env_path}\n")


# ══════════════════════════════════════════════════════
# Stage 1：測試 OmniRouter 連線
# ══════════════════════════════════════════════════════
def test_stage1():
    print("=" * 50)
    print("Stage 1：測試 OmniRouter 連線")
    print("=" * 50)

    from openai import OpenAI

    base_url = os.environ.get("OMNI_BASE_URL")
    api_key  = os.environ.get("OMNI_API_KEY")
    model    = os.environ.get("SEARCH_MODEL", "gpt-4o")

    print(f"  OMNI_BASE_URL : {base_url}")
    print(f"  OMNI_API_KEY  : {api_key[:8]}{'*' * 8}")
    print(f"  SEARCH_MODEL  : {model}\n")

    client = OpenAI(base_url=base_url, api_key=api_key)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "回覆『連線成功』四個字就好，不要其他內容。"}],
            max_tokens=20,
        )
        reply = resp.choices[0].message.content.strip()
        print(f"  ✅ 模型回覆：{reply}")
        print(f"  📊 Token 用量：in={resp.usage.prompt_tokens} out={resp.usage.completion_tokens}")
    except Exception as e:
        print(f"  ❌ 連線失敗：{e}")
        return False

    return True


# ══════════════════════════════════════════════════════
# Stage 2：測試 NewsAPI 抓新聞（只看原始資料，不過 LLM）
# ══════════════════════════════════════════════════════
def test_stage2():
    print("=" * 50)
    print("Stage 2：測試 NewsAPI 取得原始新聞")
    print("=" * 50)

    from fetchers.news_fetcher import _fetch_from_newsapi
    from datetime import date

    today = date.today().strftime("%Y-%m-%d")
    print(f"  查詢日期：{today}\n")

    try:
        articles = _fetch_from_newsapi(today)
        print(f"  ✅ 取得 {len(articles)} 篇文章\n")
        print("  前 3 篇預覽：")
        for i, a in enumerate(articles[:3], 1):
            print(f"  [{i}] {a['source']} | {a['publishedAt']}")
            print(f"       {a['title']}")
            if a['description']:
                print(f"       {a['description'][:80]}...")
            print()
    except Exception as e:
        print(f"  ❌ NewsAPI 失敗：{e}")
        return False

    return True


# ══════════════════════════════════════════════════════
# Stage 3：完整財經新聞流程（NewsAPI + LLM 整理）
# ══════════════════════════════════════════════════════
def test_stage3():
    print("=" * 50)
    print("Stage 3：完整財經新聞流程（NewsAPI → LLM → 格式化）")
    print("=" * 50)

    from fetchers.news_fetcher import fetch_daily_news
    from formatters.line_formatter import format_daily_news

    print("  正在取得並整理新聞（需要 10~30 秒）...\n")

    try:
        data = fetch_daily_news()
        print(f"  ✅ 市場氣氛：{data.get('market_sentiment')}")
        print(f"  ✅ 新聞數量：{len(data.get('news', []))}")
        print(f"  ✅ 總結：{data.get('summary')}")
        concept = data.get("finance_concept", {})
        if concept:
            print(f"  ✅ 今日概念：{concept.get('term')} — {concept.get('explanation')}")
        print()

        message = format_daily_news(data)
        print("  ── 格式化後的 Line 訊息預覽 ──")
        print(message)
        print("  ── 預覽結束 ──")
    except Exception as e:
        print(f"  ❌ 失敗：{e}")
        import traceback
        traceback.print_exc()
        return False

    return True


# ══════════════════════════════════════════════════════
# Stage 4：GitHub Trending 爬蟲
# ══════════════════════════════════════════════════════
def test_stage4():
    print("=" * 50)
    print("Stage 4：GitHub Trending 爬蟲")
    print("=" * 50)

    from fetchers.github_trending import fetch_github_trending

    try:
        repos = fetch_github_trending(limit=5)
        print(f"  ✅ 取得 {len(repos)} 個 trending repos\n")
        for r in repos:
            print(f"  #{r['rank']} {r['name']}  ({r['language']})")
            print(f"       ⭐ +{r['stars_week']} this week")
            if r['description']:
                print(f"       {r['description'][:70]}")
            print()
    except Exception as e:
        print(f"  ❌ 失敗：{e}")
        return False

    return True


# ══════════════════════════════════════════════════════
# Stage 5：Hacker News Top 10
# ══════════════════════════════════════════════════════
def test_stage5():
    print("=" * 50)
    print("Stage 5：Hacker News Top 10")
    print("=" * 50)

    from fetchers.hackernews import fetch_top_stories

    try:
        stories = fetch_top_stories(limit=5)
        print(f"  ✅ 取得 {len(stories)} 則 HN 故事\n")
        for s in stories:
            print(f"  #{s['rank']} {s['title']}")
            print(f"       👍 {s['score']} pts | 💬 {s['comments']} 則")
            print(f"       🔗 {s['hn_url']}")
            print()
    except Exception as e:
        print(f"  ❌ 失敗：{e}")
        return False

    return True


# ══════════════════════════════════════════════════════
# Stage 6：Line Bot 推播（真的會發訊息）
# ══════════════════════════════════════════════════════
def test_stage6():
    print("=" * 50)
    print("Stage 6：Line Bot 推播測試（真的會發訊息給你）")
    print("=" * 50)

    from notifiers.line_notifier import send_message

    test_msg = (
        "🧪 測試訊息\n"
        "──────────────────────\n"
        "這是 news-digest 系統的推播測試。\n"
        "如果你收到這則訊息，代表 Line Bot 推播設定正確！\n"
        "──────────────────────\n"
        "✅ LINE_CHANNEL_ACCESS_TOKEN 有效\n"
        "✅ LINE_TARGET_IDS 正確"
    )

    confirm = input("  ⚠️  這會真的發訊息給你的 Line，確認繼續？(y/N) ").strip().lower()
    if confirm != "y":
        print("  ⏭️  跳過")
        return True

    try:
        success = send_message(test_msg)
        if success:
            print("  ✅ 推播成功，請檢查你的 Line！")
        else:
            print("  ❌ 推播失敗，請確認 token 和 target ID")
            return False
    except Exception as e:
        print(f"  ❌ 失敗：{e}")
        return False

    return True


# ══════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════
STAGES = {
    "1": ("OmniRouter 連線",    test_stage1),
    "2": ("NewsAPI 原始新聞",   test_stage2),
    "3": ("完整財經新聞流程",   test_stage3),
    "4": ("GitHub Trending",    test_stage4),
    "5": ("Hacker News",        test_stage5),
    "6": ("Line Bot 推播",      test_stage6),
}

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"

    if arg == "all":
        # all 跑 1~5，6 需要手動觸發避免一直收到測試訊息
        targets = ["1", "2", "3", "4", "5"]
        print("ℹ️  all 模式會跑 Stage 1~5，Stage 6（Line 推播）需手動執行：python test_local.py 6\n")
    elif arg in STAGES:
        targets = [arg]
    else:
        print(f"❌ 不認識的 stage：{arg}")
        print(f"   可用：{', '.join(STAGES.keys())} 或 all")
        sys.exit(1)

    results = {}
    for stage_id in targets:
        name, fn = STAGES[stage_id]
        print()
        ok = fn()
        results[stage_id] = ok
        print()

    # 摘要
    if len(results) > 1:
        print("=" * 50)
        print("測試結果摘要")
        print("=" * 50)
        for sid, ok in results.items():
            icon = "✅" if ok else "❌"
            print(f"  {icon} Stage {sid}：{STAGES[sid][0]}")
        all_ok = all(results.values())
        print()
        if all_ok:
            print("🎉 全部通過！可以繼續下一步。")
        else:
            print("⚠️  有 stage 失敗，請先修正再繼續。")
