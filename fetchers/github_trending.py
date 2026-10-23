"""
github_trending.py
爬取 GitHub Trending 頁面，回傳本週 trending repos。
GitHub Trending 沒有官方 API，直接解析 HTML（結構相對穩定）。
"""

import logging
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from typing import List

logger = logging.getLogger(__name__)

TRENDING_URL = "https://github.com/trending?since=weekly&spoken_language_code=en"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class TrendingRepo:
    rank: int
    name: str          # owner/repo
    description: str
    language: str
    stars_total: str   # 總 star 數（字串，含逗號）
    stars_week: str    # 本週新增 stars
    url: str


def fetch_github_trending(limit: int = 15) -> List[dict]:
    """
    爬取 GitHub Trending（weekly），回傳前 limit 個 repo 的資訊列表。
    """
    logger.info(f"[github_trending] 開始爬取 GitHub Trending，limit={limit}")

    try:
        resp = requests.get(TRENDING_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[github_trending] 請求失敗：{e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    repo_list = soup.select("article.Box-row")

    if not repo_list:
        logger.warning("[github_trending] 找不到 repo 清單，GitHub 頁面結構可能已更新")
        return []

    results = []
    for idx, article in enumerate(repo_list[:limit], start=1):
        try:
            # repo 名稱
            name_tag = article.select_one("h2 a")
            name = name_tag["href"].lstrip("/") if name_tag else "unknown/unknown"
            url = f"https://github.com/{name}"

            # 描述
            desc_tag = article.select_one("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # 語言
            lang_tag = article.select_one('[itemprop="programmingLanguage"]')
            language = lang_tag.get_text(strip=True) if lang_tag else "N/A"

            # 總 star 數
            star_tag = article.select("a.Link--muted")
            stars_total = star_tag[0].get_text(strip=True) if star_tag else "0"

            # 本週新增 stars
            week_star_tag = article.select_one("span.d-inline-block.float-sm-right")
            stars_week = week_star_tag.get_text(strip=True) if week_star_tag else "N/A"
            # 清理格式：" 1,234 stars this week" → "1,234"
            stars_week = (
                stars_week.replace("stars this week", "")
                          .replace("star this week", "")
                          .strip()
            )

            repo = TrendingRepo(
                rank=idx,
                name=name,
                description=description,
                language=language,
                stars_total=stars_total,
                stars_week=stars_week,
                url=url,
            )
            results.append(asdict(repo))

        except Exception as e:
            logger.warning(f"[github_trending] 解析第 {idx} 個 repo 失敗：{e}")
            continue

    logger.info(f"[github_trending] 成功取得 {len(results)} 個 trending repos")
    return results
