"""
hackernews.py
透過 Hacker News 官方 Firebase API 取得 Top Stories 前 10 名。
官方 API 文件：https://github.com/HackerNews/API
完全免費，不需要 API key。
"""

import logging
import requests
from dataclasses import dataclass, asdict
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

HN_BASE = "https://hacker-news.firebaseio.com/v0"
TOP_STORIES_URL = f"{HN_BASE}/topstories.json"
ITEM_URL = f"{HN_BASE}/item/{{item_id}}.json"


@dataclass
class HNStory:
    rank: int
    id: int
    title: str
    url: str           # 原始連結（可能為空，表示是 HN 自己的討論串）
    hn_url: str        # Hacker News 討論頁連結
    score: int
    by: str            # 作者
    comments: int      # 留言數


def _fetch_item(item_id: int) -> Optional[dict]:
    """取得單一 HN 項目的詳細資訊"""
    try:
        resp = requests.get(ITEM_URL.format(item_id=item_id), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"[hackernews] 取得 item {item_id} 失敗：{e}")
        return None


def fetch_top_stories(limit: int = 10) -> List[dict]:
    """
    取得 HN Top Stories 前 limit 名。
    使用 ThreadPoolExecutor 平行取得各 story 詳情，加速請求。
    """
    logger.info(f"[hackernews] 開始取得 HN Top {limit} Stories")

    # Step 1: 取得 top story IDs 列表
    try:
        resp = requests.get(TOP_STORIES_URL, timeout=10)
        resp.raise_for_status()
        top_ids = resp.json()[:limit]
    except Exception as e:
        logger.error(f"[hackernews] 取得 top stories 清單失敗：{e}")
        return []

    # Step 2: 平行取得各 story 詳情
    items = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_item, item_id): item_id for item_id in top_ids}
        for future in as_completed(futures):
            item_id = futures[future]
            data = future.result()
            if data:
                items[item_id] = data

    # Step 3: 按原始排名排序並整理格式
    results = []
    for rank, item_id in enumerate(top_ids, start=1):
        data = items.get(item_id)
        if not data:
            continue

        story = HNStory(
            rank=rank,
            id=item_id,
            title=data.get("title", ""),
            url=data.get("url", ""),          # 外部連結（可能是空字串）
            hn_url=f"https://news.ycombinator.com/item?id={item_id}",
            score=data.get("score", 0),
            by=data.get("by", ""),
            comments=data.get("descendants", 0),
        )
        results.append(asdict(story))

    logger.info(f"[hackernews] 成功取得 {len(results)} 則 HN Top Stories")
    return results
