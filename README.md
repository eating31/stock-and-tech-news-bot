# 📰 News Digest — 每日財經 + 每週科技週報自動推播

自動整理全球財經新聞與科技動態，每天早上推播到 Line Bot。

- **每日財經情報**：5～7 條影響台灣大盤的全球重點新聞 + 市場氣氛判斷 + 每日金融小知識
- **每週科技週報**：GitHub Trending 精選 + Hacker News 亮點，由 AI 整理成可讀摘要

---

## 架構

```
NewsAPI（抓今日財經原文）
        ↓
OmniRouter → LLM（分析 + 翻譯 + 整理）
        ↓
Line Bot 推播
```

```
GitHub Trending（爬蟲）
Hacker News API（官方免費）
        ↓
OmniRouter → LLM（整理成週報摘要）
        ↓
Line Bot 推播
```

**OmniRouter** 是一個 GitHub Copilot API proxy，讓你用已有的 Copilot 訂閱存取 LLM，不需要額外申請 OpenAI API key。

---

## 專案結構

```
news-digest/
├── fetchers/
│   ├── news_fetcher.py       # NewsAPI + LLM 整理財經新聞
│   ├── github_trending.py    # GitHub Trending 爬蟲
│   └── hackernews.py         # Hacker News 官方 API
├── formatters/
│   └── line_formatter.py     # 訊息格式化 + prompt 定義
├── notifiers/
│   └── line_notifier.py      # Line Messaging API 推播
├── main_daily.py             # 每日財經新聞主程式
├── main_weekly.py            # 每週科技週報主程式
├── test_local.py             # 本地階段性測試
├── Dockerfile
├── docker-compose.yml        # OmniRouter + news-digest
└── .env.example              # 環境變數範例
```

---

## 快速開始

### 1. 取得必要的 API Key

| 服務 | 用途 | 取得方式 |
|------|------|---------|
| [NewsAPI](https://newsapi.org/register) | 每日財經新聞來源 | 免費申請，每天 100 次請求 |
| [Line Developers](https://developers.line.biz/console/) | 推播通知 | 建立 Messaging API Channel，取得 Channel Access Token |
| OmniRouter | GitHub Copilot API proxy | 自行架設，參考 [OmniRouter](https://github.com/your-org/omni-router) |

### 2. 設定環境變數

```bash
cp .env.example .env
# 用編輯器開啟 .env 填入以下值
```

| 變數 | 說明 |
|------|------|
| `OMNI_API_KEY` | 打進 OmniRouter 的 API key |
| `OMNI_BASE_URL` | OmniRouter endpoint（本機：`http://localhost:20128/v1`）|
| `SEARCH_MODEL` | 使用的模型，例如 `auto/best-chat` 或 `gh/claude-sonnet-5` |
| `NEWS_API_KEY` | NewsAPI key |
| `LINE_CHANNEL_ACCESS_TOKEN` | Line Bot Channel Access Token |
| `LINE_TARGET_IDS` | 推播對象 ID，逗號分隔（User ID 以 `U` 開頭）|

> ⚠️ `.env` 已加入 `.gitignore`，**絕對不要 commit 到 git**。

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

### 4. 本地測試

```bash
# 分階段測試，確認每個環節都正常
python3 test_local.py 1   # OmniRouter 連線
python3 test_local.py 2   # NewsAPI 取得原始新聞
python3 test_local.py 3   # 完整財經流程（NewsAPI → LLM → 格式化）
python3 test_local.py 4   # GitHub Trending 爬蟲
python3 test_local.py 5   # Hacker News
python3 test_local.py 6   # Line Bot 推播（會真的發訊息）
```

### 5. 執行

```bash
# 每日財經新聞
python3 main_daily.py

# 每週科技週報
python3 main_weekly.py
```

---

## 取得 Line User ID

把 Bot 加入 Line 後，傳任意訊息給它，從 webhook event 的 `source.userId` 取得。
若沒有 webhook server，可以用 [Line API 的 getProfile](https://developers.line.biz/en/reference/messaging-api/#get-profile) 或透過 [LINE Bot Designer](https://developers.line.biz/en/services/bot-designer/) 查詢。

---

## GCP 部署（選用）

本地測試完成後，可部署到 GCP 實現全自動排程，容器執行完畢後自動關閉，不需要 24 小時常駐。

```
Cloud Scheduler → Cloud Run Job → 執行完畢停止
```

詳細部署步驟請參考 [`.kiro/specs/news-digest/tasks.md`](.kiro/specs/news-digest/tasks.md) 的 Phase 5。

---

## 注意事項

- 本工具整理的財經資訊**僅供個人參考，不構成投資建議**
- NewsAPI 免費方案有每日請求上限，超過需升級方案
- GitHub Trending 為 HTML 爬蟲，若 GitHub 改版可能需要更新解析邏輯

---

## License

MIT
