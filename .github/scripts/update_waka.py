"""Update the WakaTime section of README.md using a WakaTime OAuth access token."""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BLOCKS = "░▒▓█"
WIDTH = 25


def fetch_stats(token, time_range):
    req = urllib.request.Request(
        f"https://wakatime.com/api/v1/users/current/stats/{time_range}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    for _ in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    return json.load(resp)["data"]
                # 202: WakaTime is still calculating the stats
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            sys.exit(f"WakaTime API error {e.code}: {body}")
        time.sleep(20)
    sys.exit("WakaTime stats were not ready after retries")


def make_bar(percent):
    value = percent / 100 * WIDTH
    full = int(value)
    bar = BLOCKS[-1] * full
    if full < WIDTH:
        bar += BLOCKS[round((value - full) * (len(BLOCKS) - 1))]
        bar += BLOCKS[0] * (WIDTH - full - 1)
    return bar


def render(data, lang_count, show_total):
    lines = []
    if show_total:
        lines += [f"Total Time: {data['human_readable_total']}", ""]
    for lang in data["languages"][:lang_count]:
        lines.append(
            f"{lang['name']:<20}{lang['text']:<22}"
            f"{make_bar(lang['percent'])}   {lang['percent']:05.2f} %"
        )
    return "```txt\n" + "\n".join(lines) + "\n```"


def update_readme(path, section, content):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    pattern = re.compile(
        rf"(<!--START_SECTION:{re.escape(section)}-->)(.*?)(<!--END_SECTION:{re.escape(section)}-->)",
        re.S,
    )
    if not pattern.search(src):
        sys.exit(f"Markers for section '{section}' not found in {path}")
    out = pattern.sub(lambda m: f"{m.group(1)}\n\n{content}\n\n{m.group(3)}", src)
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)


def main():
    token = os.environ["WAKATIME_ACCESS_TOKEN"]
    data = fetch_stats(token, os.environ.get("TIME_RANGE", "last_7_days"))
    content = render(
        data,
        int(os.environ.get("LANG_COUNT", "5")),
        os.environ.get("SHOW_TOTAL", "true").lower() == "true",
    )
    update_readme("README.md", os.environ.get("SECTION_NAME", "waka"), content)


if __name__ == "__main__":
    main()
