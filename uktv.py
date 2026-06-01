#!/usr/bin/env python3
"""
Stalker to M3U converter

Output:
  uktv.m3u - UK live TV
"""

import os
import sys
import re
import requests
from datetime import datetime

# ========== CONFIG ==========

EPG_URL = "https://epg.pw/xmltv.xml"

EXCLUDE_KEYWORDS = ["test", "xxx", "adult", "18+", "erotic"]

UK_KEYWORDS = [
    "uk", "gb", "eng", "english",
    "bbc", "itv", "sky", "bt sport",
    "channel 4", "channel 5",
    "dave", "gold", "yesterday", "film4",
    "sky sports", "sky cinema"
]

# ========== NAME CLEANING ==========

def clean_channel_name(name):
    name = name.strip()

    # ✅ keep only UK|
    if re.match(r'^UK\|\s*', name):
        return name

    # ❌ remove ANY other prefix like DK|, US| etc.
    name = re.sub(r'^[A-Z]{2}\|\s*', '', name)

    # ✅ force UK|
    return f"UK| {name}"

# ========== FILTERS ==========

def is_uk(name, group):
    text = (name + " " + group).lower()
    return any(k in text for k in UK_KEYWORDS)

def should_exclude(name, group):
    text = (name + " " + group).lower()
    return any(k in text for k in EXCLUDE_KEYWORDS)

# ========== STALKER CLIENT ==========

class StalkerLite:
    def __init__(self, url, mac, token):
        self.mac = mac.upper().strip()
        self.token = token
        self.base_url = url.rstrip('/')
        self.session = requests.Session()

    def _headers(self):
        return {
            "User-Agent": "Mozilla/5.0",
            "Cookie": f"mac={self.mac}; stb_lang=en; timezone=GMT",
            "Authorization": f"Bearer {self.token}"
        }

    def _get(self, url):
        try:
            r = self.session.get(url, headers=self._headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("js") if "js" in data else data
        except Exception:
            pass
        return None

    def get_channels(self):
        url = f"{self.base_url}/portal.php?type=itv&action=get_all_channels&JsHttpRequest=1-xml"
        data = self._get(url)

        if not data:
            return []

        if isinstance(data, dict):
            return data.get("data", []) or []
        return data

    def create_link(self, cmd):
        cmd = (cmd or "").strip()

        # remove ffmpeg prefix
        if cmd.lower().startswith("ffmpeg "):
            cmd = cmd[7:].strip()

        # extract URL
        match = re.search(r"https?://[^\s]+", cmd)
        if match:
            return match.group(0)

        return ""

# ========== HELPERS ==========

def parse_mac_list(file):
    portals = []
    with open(file) as f:
        for line in f:
            if "," in line:
                url, mac = line.strip().split(",")
                portals.append((url.strip(), mac.strip()))
    return portals

def get_token(url, mac):
    try:
        full = f"{url.rstrip('/')}/portal.php?type=stb&action=handshake&JsHttpRequest=1-xml"
        r = requests.get(full, headers={
            "Cookie": f"mac={mac}",
            "User-Agent": "Mozilla/5.0"
        }, timeout=5)
        data = r.json()
        return data["js"]["token"]
    except Exception:
        return None

# ========== PLAYLIST WRITER ==========

UA = "Mozilla/5.0"

def esc(s):
    return str(s).replace('"', "&quot;")

def write_extinf(f, name, logo, mac, token, url):
    clean_name = clean_channel_name(name)

    f.write(
        f'#EXTINF:-1 tvg-name="{esc(clean_name)}" tvg-logo="{esc(logo)}" group-title="UK",{esc(clean_name)}\n'
    )
    f.write(f'#EXTVLCOPT:http-user-agent={UA}\n')
    f.write(f'#EXTVLCOPT:http-cookie=mac={mac}\n')
    if token:
        f.write(f'#EXTVLCOPT:http-header=Authorization: Bearer {token}\n')
    f.write(f"{url}\n")

# ========== GENERATOR ==========

def generate_playlist(portals, output="uktv.m3u"):
    now = datetime.now().isoformat()

    print("Creating playlist file...")
    total = 0

    with open(output, "w", encoding="utf-8") as f:
        f.write(f'#EXTM3U x-tvg-url="{EPG_URL}"\n')
        f.write(f"# UK Playlist | Generated: {now}\n\n")

        for url, mac, stalker in portals:
            print(f"Processing: {url}")

            channels = stalker.get_channels()
            print(f"  Channels found: {len(channels)}")

            for ch in channels:
                if not isinstance(ch, dict):
                    continue

                name = ch.get("name", "")
                group = ch.get("genre_name") or ch.get("tv_genre") or "General"
                logo = ch.get("logo", "")

                if should_exclude(name, group):
                    continue

                if not is_uk(name, group):
                    continue

                stream = stalker.create_link(ch.get("cmd", ""))
                if not stream:
                    continue

                write_extinf(f, name, logo, mac, stalker.token, stream)
                total += 1

    print(f"\n✅ uktv.m3u generated with {total} UK channels")

# ========== MAIN ==========

def main():
    mac_file = sys.argv[1] if len(sys.argv) > 1 else "mac_list.txt"

    if not os.path.exists(mac_file):
        print("mac_list.txt not found")
        open("uktv.m3u", "w").close()
        return

    raw = parse_mac_list(mac_file)
    portals = []

    for url, mac in raw:
        print(f"Testing {url}")

        token = get_token(url, mac)

        if not token:
            print(" -> failed")
            continue

        print(" -> OK")
        stalker = StalkerLite(url, mac, token)
        portals.append((url, mac, stalker))

    if not portals:
        print("No working portals — creating empty playlist")
        open("uktv.m3u", "w").close()
        return

    generate_playlist(portals, "uktv.m3u")

if __name__ == "__main__":
    main()
