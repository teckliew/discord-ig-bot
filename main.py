"""
Instagram -> Discord auto-poster
Polls your own Instagram Professional account via the official Instagram Graph API
and posts new media to a Discord channel via webhook.

Requires:
- Instagram account converted to Professional (Business or Creator)
- That account linked to a Facebook Page you control
- A Meta App with Instagram Graph API access + a long-lived access token
- A Discord webhook URL for the target channel

See SETUP.md for how to get the IG_USER_ID and ACCESS_TOKEN.
"""

import os
import json
import time
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

IG_USER_ID = os.environ["IG_USER_ID"]
ACCESS_TOKEN = os.environ["IG_ACCESS_TOKEN"]
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", 300))  # 5 min default
STATE_FILE = Path(__file__).parent / "state.json"

GRAPH_API_VERSION = "v21.0"
MEDIA_FIELDS = "id,caption,media_type,media_url,permalink,timestamp,thumbnail_url"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("ig-discord-bot")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_seen_id": None}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_latest_media(limit: int = 10) -> list[dict]:
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{IG_USER_ID}/media"
    params = {
        "fields": MEDIA_FIELDS,
        "access_token": ACCESS_TOKEN,
        "limit": limit,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", [])


DISCORD_UPLOAD_LIMIT_BYTES = int(os.environ.get("DISCORD_UPLOAD_LIMIT_MB", 25)) * 1024 * 1024


def post_to_discord(media: dict) -> bool:
    media_type = media.get("media_type")
    if media_type == "VIDEO":
        return post_video_to_discord(media)
    else:
        return post_image_to_discord(media)


def post_image_to_discord(media: dict) -> bool:
    caption = media.get("caption", "") or ""
    if len(caption) > 300:
        caption = caption[:297] + "..."

    embed = {
        "title": "New Instagram Post",
        "url": media.get("permalink"),
        "description": caption,
        "timestamp": media.get("timestamp"),
        "color": 0xE1306C,  # Instagram-ish pink
    }
    image_url = media.get("media_url")
    if image_url:
        embed["image"] = {"url": image_url}

    payload = {
        "content": media.get("permalink"),
        "embeds": [embed],
    }

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=30)
    except requests.RequestException as e:
        log.error("Discord webhook request errored for image post %s: %s", media.get("id"), e)
        return False

    if resp.status_code >= 300:
        log.error("Discord webhook failed (%s): %s", resp.status_code, resp.text)
        return False

    log.info("Posted new image post %s to Discord", media.get("id"))
    return True


def post_video_to_discord(media: dict) -> bool:
    """
    Downloads the video from Instagram's CDN and re-uploads it as a Discord
    attachment, so it plays natively in-channel instead of just linking out.
    Falls back to a link-only post if the file is missing or too large.
    """
    caption = media.get("caption", "") or ""
    if len(caption) > 300:
        caption = caption[:297] + "..."

    video_url = media.get("media_url")
    if not video_url:
        log.warning("No media_url for video %s, falling back to link post", media.get("id"))
        return _post_video_link_fallback(media, caption)

    try:
        video_resp = requests.get(video_url, stream=True, timeout=60)
        video_resp.raise_for_status()

        content_length = int(video_resp.headers.get("Content-Length", 0))
        if content_length and content_length > DISCORD_UPLOAD_LIMIT_BYTES:
            log.warning(
                "Video %s is %.1fMB, over the %.0fMB upload limit; falling back to link post",
                media.get("id"), content_length / 1024 / 1024, DISCORD_UPLOAD_LIMIT_BYTES / 1024 / 1024,
            )
            return _post_video_link_fallback(media, caption)

        video_bytes = video_resp.content
        if len(video_bytes) > DISCORD_UPLOAD_LIMIT_BYTES:
            log.warning("Video %s exceeded upload limit after download; falling back to link post", media.get("id"))
            return _post_video_link_fallback(media, caption)

    except requests.RequestException as e:
        log.error("Failed to download video %s: %s", media.get("id"), e)
        return _post_video_link_fallback(media, caption)

    payload_json = {
        "content": f"**New Instagram Video**\n{caption}\n{media.get('permalink')}",
    }
    files = {
        "file1": ("instagram_video.mp4", video_bytes, "video/mp4"),
    }
    data = {"payload_json": json.dumps(payload_json)}

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, data=data, files=files, timeout=60)
    except requests.RequestException as e:
        log.error("Discord webhook request errored for video upload %s: %s", media.get("id"), e)
        return _post_video_link_fallback(media, caption)

    if resp.status_code >= 300:
        log.error("Discord video upload failed (%s): %s", resp.status_code, resp.text)
        return _post_video_link_fallback(media, caption)

    log.info("Uploaded video %s to Discord as a native attachment", media.get("id"))
    return True


def _post_video_link_fallback(media: dict, caption: str) -> bool:
    media_type = media.get("media_type")
    image_url = media.get("media_url") if media_type != "VIDEO" else media.get("thumbnail_url")

    embed = {
        "title": "New Instagram Post",
        "url": media.get("permalink"),
        "description": caption,
        "timestamp": media.get("timestamp"),
        "color": 0xE1306C,  # Instagram-ish pink
    }
    if image_url:
        embed["image"] = {"url": image_url}

    payload = {
        "content": media.get("permalink"),  # plain link so Discord/mobile can preview reliably too
        "embeds": [embed],
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=30)
    except requests.RequestException as e:
        log.error("Discord fallback link post errored for %s: %s", media.get("id"), e)
        return False

    if resp.status_code >= 300:
        log.error("Discord fallback link post failed (%s): %s", resp.status_code, resp.text)
        return False

    log.info("Posted video %s as link fallback (too large or download failed)", media.get("id"))
    return True


def run_once(state: dict) -> tuple[dict, bool]:
    """Returns (state, success). success=False on API failures (e.g. expired
    token) so callers like run_single.py can exit non-zero and trigger alerts."""
    try:
        media_list = fetch_latest_media()
    except requests.RequestException as e:
        log.error("Failed to fetch Instagram media: %s", e)
        return state, False

    if not media_list:
        return state, True

    last_seen_id = state.get("last_seen_id")

    if last_seen_id is None:
        # First run: just record the newest post, don't spam-post the whole history
        state["last_seen_id"] = media_list[0]["id"]
        save_state(state)
        log.info("Initialized with latest post %s (no backlog posted)", media_list[0]["id"])
        return state, True

    # media_list is newest-first; find anything newer than last_seen_id
    new_items = []
    for item in media_list:
        if item["id"] == last_seen_id:
            break
        new_items.append(item)

    all_posts_succeeded = True
    for item in reversed(new_items):  # post oldest-of-the-new first
        if not post_to_discord(item):
            all_posts_succeeded = False

    if new_items:
        # Advance the cursor even if a post failed, so we don't re-post the
        # same item forever on every future run. The failure alert (via the
        # GitHub Actions workflow) is what tells you to go check what happened.
        state["last_seen_id"] = media_list[0]["id"]
        save_state(state)

    return state, all_posts_succeeded


def main() -> None:
    state = load_state()
    log.info("Starting IG -> Discord poller (interval=%ss)", POLL_INTERVAL_SECONDS)
    while True:
        state, _ = run_once(state)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()