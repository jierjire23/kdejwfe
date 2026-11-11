import os
import json
import asyncio
from datetime import datetime, timezone

import aiohttp

ELDORADO_API_URL = os.getenv("ELDORADO_API_URL")
STATE_FILE = "state.json"
SUMMARY_FILE = os.getenv("GITHUB_STEP_SUMMARY")

if not ELDORADO_API_URL:
    raise RuntimeError("Missing ELDORADO_API_URL")


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)


def write_summary(text):
    print(text)
    if SUMMARY_FILE:
        with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")


async def get_first_offer_title():
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            ELDORADO_API_URL,
            headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
        ) as response:
            if response.status != 200:
                write_summary(f"## ❌ Eldorado API returned HTTP {response.status}")
                return None
            data = await response.json()
    results = data.get("results", [])
    if not results:
        write_summary("## ❌ API returned no results")
        return None
    return results[0].get("offer", {}).get("offerTitle")


async def main():
    current = await get_first_offer_title()
    if current is None:
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    state = load_state()
    last = state.get("last_offer_title")

    if last is None:
        state = {"last_offer_title": current, "last_changed_at": now, "history": []}
        save_state(state)
        write_summary(f"## ✅ First check\nCurrent first offer:\n\n**{current}**")
    elif current == last:
        write_summary(
            f"## ✅ No change ({now})\nFirst offer:\n\n**{current}**\n\n"
            f"Last change: {state.get('last_changed_at')}"
        )
    else:
        history = state.get("history", [])
        history.insert(0, {"at": now, "old": last, "new": current})
        state = {
            "last_offer_title": current,
            "last_changed_at": now,
            "history": history[:50],
        }
        save_state(state)
        write_summary(
            f"## 🚨 ALGORITHM CHANGED ({now})\n**Old:** {last}\n\n**New:** {current}"
        )


asyncio.run(main())
