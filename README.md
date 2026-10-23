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

## 環境需求

- Python 3.12+
- Docker + Docker Compose
- 本機已安裝並設定好 [OmniRouter](https://github.com/diegosouzapw/OmniRoute)（需連接 GitHub Copilot）

---

## 快速開始

### 1. 取得必要的 API Key

| 服務 | 用途 | 取得方式 |
|------|------|---------|
| [NewsAPI](https://newsapi.org/register) | 每日財經新聞來源 | 免費申請，每天 100 次請求 |
| [Line Developers](https://developers.line.biz/console/) | 推播通知 | 建立 Messaging API Channel，取得 Channel Access Token |
| OmniRouter | GitHub Copilot API proxy | 本機自行安裝，見下方說明 |

### 2. 設定環境變數

```bash
cp .env.example .env
```

填入以下 8 個變數：

| 變數 | 說明 |
|------|------|
| `OMNI_API_KEY` | 打進 OmniRouter 的 API key |
| `STORAGE_ENCRYPTION_KEY` | OmniRouter SQLite 加密金鑰，從 `~/.omniroute/.env` 複製 |
| `OMNI_BASE_URL` | OmniRouter endpoint（本機：`http://localhost:20128/v1`）|
| `OMNI_ROUTER_IMAGE` | OmniRouter Docker image 名稱 |
| `SEARCH_MODEL` | 使用的模型，例如 `auto/best-chat` 或 `gh/claude-sonnet-5` |
| `NEWS_API_KEY` | NewsAPI key |
| `LINE_CHANNEL_ACCESS_TOKEN` | Line Bot Channel Access Token |
| `LINE_TARGET_IDS` | 推播對象 ID，逗號分隔（User ID 以 `U` 開頭）|

> ⚠️ `.env` 已加入 `.gitignore`，**絕對不要 commit 到 git**。

### 3. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

---

## 方式 A：直接用 Python 執行（本機開發）

OmniRouter 需要先在背景跑著（`http://localhost:20128`），然後：

```bash
# 分階段測試，確認每個環節都正常
python3 test_local.py 1   # OmniRouter 連線
python3 test_local.py 2   # NewsAPI 取得原始新聞
python3 test_local.py 3   # 完整財經流程（NewsAPI → LLM → 格式化）
python3 test_local.py 4   # GitHub Trending 爬蟲
python3 test_local.py 5   # Hacker News
python3 test_local.py 6   # Line Bot 推播（會真的發訊息）

# 全部通過後直接執行
python3 main_daily.py
python3 main_weekly.py
```

---

## 方式 B：Docker Compose 執行

用 Docker Compose 把 OmniRouter 和 news-digest 一起跑，適合部署到伺服器或 GCP。

### Step 1：備份本機 OmniRouter 設定

OmniRouter 的所有設定（provider credentials、API key 等）存在 SQLite 裡。
先在本機備份：

```bash
omniroute backup create --name gcp-migration
# 備份檔位於 ~/.omniroute/backups/omniroute-backup-gcp-migration/
```

### Step 2：建立 Docker volume 並匯入備份

```bash
# 建立 volume
docker volume create news-digest_omniroute-data

# 將備份的 SQLite 複製進 volume
docker run --rm \
  -v news-digest_omniroute-data:/app/data \
  -v ~/.omniroute/backups/omniroute-backup-gcp-migration:/backup:ro \
  alpine \
  cp /backup/storage.sqlite /app/data/storage.sqlite

# 修正 volume 內的檔案權限（OmniRouter 用 UID 1000 執行）
docker run --rm \
  -v news-digest_omniroute-data:/app/data \
  alpine \
  chown -R 1000:1000 /app/data

# 確認檔案已正確複製
docker run --rm \
  -v news-digest_omniroute-data:/app/data \
  alpine \
  ls -lh /app/data/
```

### Step 3：確認 `.env` 包含 `STORAGE_ENCRYPTION_KEY`

```bash
cat ~/.omniroute/.env | grep STORAGE_ENCRYPTION_KEY
```

把這個值填入專案的 `.env`：

```
STORAGE_ENCRYPTION_KEY=你的加密金鑰
```

### Step 4：啟動 OmniRouter 確認正常

```bash
docker compose up -d omni-router

# 等約 20 秒後確認狀態
docker compose ps
# STATUS 應顯示 healthy

# 瀏覽器開啟 Dashboard 確認 provider 連接正常
open http://localhost:20128
```

> 首次啟動如果需要重設 Dashboard 密碼，進入 container 執行：
> ```bash
> docker compose exec -u root omni-router sh
> cd /app && node -e "const b=require('bcryptjs');const D=require('better-sqlite3');const h=b.hashSync('your-new-password',12);const db=new D('data/storage.sqlite');db.prepare(\"UPDATE key_value SET value=? WHERE namespace='settings' AND key='password'\").run(JSON.stringify(h));console.log('done');db.close();"
> exit
> docker compose restart omni-router
> ```

### Step 5：執行每日財經新聞

```bash
docker compose run --rm news-digest python main_daily.py
```

### Step 6：執行每週科技週報

```bash
docker compose run --rm news-digest python main_weekly.py
```

### 清理

```bash
docker compose down
```

---

## 取得 Line User ID

把 Bot 加入 Line 後傳任意訊息，從 webhook event 的 `source.userId` 取得（以 `U` 開頭的字串）。

---

## GCP 部署（選用）

本地 Docker Compose 測試完成後，可部署到 GCP 實現全自動排程。
容器執行完畢後自動關閉，不需要 24 小時常駐，費用幾乎為零。

```
Cloud Scheduler → Cloud Run Job → 執行完畢停止
```

所需 GCP 服務（全部在免費額度內）：

| 服務 | 用途 |
|------|------|
| Cloud Run Jobs | 執行排程任務 |
| Cloud Scheduler | 每天 07:00 / 每週一 08:00 觸發 |
| Cloud Storage | 存放 OmniRouter SQLite（掛載到 `/app/data`）|
| Artifact Registry | 存放 Docker image |
| Secret Manager | 存放敏感環境變數 |

詳細部署步驟請參考 [`.kiro/specs/news-digest/tasks.md`](.kiro/specs/news-digest/tasks.md) 的 Phase 5。

---

## 注意事項

- 本工具整理的財經資訊**僅供個人參考，不構成投資建議**
- NewsAPI 免費方案每日 100 次請求上限，本系統每天約用 2 次，綽綽有餘
- GitHub Trending 為 HTML 爬蟲，若 GitHub 改版可能需要更新解析邏輯
- OmniRouter 的 `STORAGE_ENCRYPTION_KEY` 務必妥善保管，遺失後無法解密已儲存的 credentials

---

## License

MIT
