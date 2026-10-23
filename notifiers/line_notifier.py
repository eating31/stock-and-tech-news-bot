"""
line_notifier.py
透過 Line Messaging API 推播訊息給指定用戶或群組。
使用 Channel Access Token（長期 token），不需要 webhook。
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

LINE_API_URL = "https://api.line.me/v2/bot/message/push"
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# 支援同時推給多個 user_id 或 group_id（逗號分隔）
# 例如：LINE_TARGET_IDS=Uxxxx,Cxxxx
_raw_targets = os.environ.get("LINE_TARGET_IDS", "")
LINE_TARGET_IDS = [t.strip() for t in _raw_targets.split(",") if t.strip()]

MAX_MESSAGE_LENGTH = 5000  # Line 單則訊息上限


def _split_message(text: str) -> list[str]:
    """
    若訊息超過 Line 上限（5000 字），分段傳送。
    盡量在換行處切割，避免切斷句子。
    """
    if len(text) <= MAX_MESSAGE_LENGTH:
        return [text]

    chunks = []
    while len(text) > MAX_MESSAGE_LENGTH:
        split_at = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
        if split_at == -1:
            split_at = MAX_MESSAGE_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def send_message(text: str, target_ids: list[str] | None = None) -> bool:
    """
    推播文字訊息。
    target_ids 若為 None，使用環境變數 LINE_TARGET_IDS。
    回傳是否全部成功。
    """
    targets = target_ids or LINE_TARGET_IDS

    if not LINE_CHANNEL_TOKEN:
        logger.error("[line_notifier] LINE_CHANNEL_ACCESS_TOKEN 未設定")
        return False

    if not targets:
        logger.error("[line_notifier] LINE_TARGET_IDS 未設定，無法推播")
        return False

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
    }

    chunks = _split_message(text)
    all_success = True

    for target_id in targets:
        for chunk in chunks:
            payload = {
                "to": target_id,
                "messages": [{"type": "text", "text": chunk}],
            }
            try:
                resp = requests.post(LINE_API_URL, headers=headers, json=payload, timeout=10)
                if resp.status_code == 200:
                    logger.info(f"[line_notifier] 推播成功 → {target_id[:8]}...")
                else:
                    logger.error(
                        f"[line_notifier] 推播失敗 → {target_id[:8]}... "
                        f"status={resp.status_code} body={resp.text[:200]}"
                    )
                    all_success = False
            except requests.RequestException as e:
                logger.error(f"[line_notifier] 網路錯誤：{e}")
                all_success = False

    return all_success
