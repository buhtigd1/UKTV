#!/usr/bin/env python3

import requests
import html
import json

SOURCE_URL = "https://raw.githubusercontent.com/bugsfreeweb/LiveTVCollector/main/LiveTV/UK/LiveTV"
OUTPUT_FILE = "uktv.m3u"

def main():
    response = requests.get(SOURCE_URL, timeout=30)
    response.raise_for_status()

    channels = response.json()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as m3u:
        m3u.write("#EXTM3U\n")

        for ch in channels:
            name = html.unescape(ch.get("name", "Unknown"))
            group = html.unescape(ch.get("type", "Other"))
            logo = ch.get("img", "")
            url = ch.get("url", "")

            if not url:
                continue

            m3u.write(
                f'#EXTINF:-1 tvg-name="{name}" '
                f'tvg-logo="{logo}" '
                f'group-title="{group}",{name}\n'
            )
            m3u.write(f"{url}\n")

    print(f"Saved {len(channels)} channels to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
