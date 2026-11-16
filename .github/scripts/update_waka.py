"""Render a WakaTime stats card (SVG) and embed it in README.md.

Uses a WakaTime OAuth access token (WAKATIME_ACCESS_TOKEN).
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from xml.sax.saxutils import escape

SVG_PATH = "assets/waka-stats.svg"
COLORS = ["#4f8cff", "#a371f7", "#2ea98f", "#f0883e", "#e5534b", "#768390"]
RANGE_LABELS = {
    "last_7_days": "last 7 days",
    "last_30_days": "last 30 days",
    "last_6_months": "last 6 months",
    "last_year": "last year",
    "all_time": "all time",
}


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


def render_svg(data, lang_count, time_range):
    width, pad = 495, 24
    inner = width - 2 * pad
    langs = data["languages"][:lang_count]
    row_h, top = 48, 104
    height = top + len(langs) * row_h + 4
    label = RANGE_LABELS.get(time_range, time_range.replace("_", " "))

    rows = []
    for i, lang in enumerate(langs):
        y = top + i * row_h
        color = COLORS[i % len(COLORS)]
        pct = lang["percent"]
        fill_w = max(inner * pct / 100, 6) if pct > 0 else 0
        rows.append(
            f'<text class="name" x="{pad}" y="{y}">{escape(lang["name"])}</text>'
            f'<text class="meta" x="{width - pad}" y="{y}" text-anchor="end">'
            f'{escape(lang["text"])}  ·  {pct:.1f}%</text>'
            f'<rect class="track" x="{pad}" y="{y + 10}" width="{inner}" height="8" rx="4"/>'
            f'<rect x="{pad}" y="{y + 10}" width="{fill_w:.1f}" height="8" rx="4" fill="{color}"/>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="WakaTime: {escape(data['human_readable_total'])} coding time in the {label}">
<style>
  text {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; fill: #1f2328; }}
  .card {{ fill: #ffffff; stroke: #d0d7de; }}
  .track {{ fill: #eaeef2; }}
  .eyebrow {{ font-size: 12px; fill: #656d76; letter-spacing: .08em; text-transform: uppercase; }}
  .total {{ font-size: 30px; font-weight: 700; }}
  .sub {{ font-size: 13px; fill: #656d76; }}
  .name {{ font-size: 14px; font-weight: 600; }}
  .meta {{ font-size: 13px; fill: #656d76; }}
  @media (prefers-color-scheme: dark) {{
    text {{ fill: #e6edf3; }}
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .track {{ fill: #21262d; }}
    .eyebrow, .sub, .meta {{ fill: #8b949e; }}
  }}
</style>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" class="card"/>
<text class="eyebrow" x="{pad}" y="34">Coding time</text>
<text class="total" x="{pad}" y="68">{escape(data['human_readable_total'])}</text>
<text class="sub" x="{width - pad}" y="68" text-anchor="end">{label}</text>
{chr(10).join(rows)}
</svg>
"""


def alt_text(data, lang_count):
    parts = [f"{l['name']} {l['text']}" for l in data["languages"][:lang_count]]
    return f"WakaTime, total {data['human_readable_total']}: " + ", ".join(parts)


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
    time_range = os.environ.get("TIME_RANGE", "last_7_days")
    lang_count = int(os.environ.get("LANG_COUNT", "5"))
    data = fetch_stats(token, time_range)

    os.makedirs(os.path.dirname(SVG_PATH), exist_ok=True)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(render_svg(data, lang_count, time_range))

    img = f'<img src="{SVG_PATH}" alt="{escape(alt_text(data, lang_count), {chr(34): "&quot;"})}" width="495">'
    update_readme("README.md", os.environ.get("SECTION_NAME", "waka"), img)


if __name__ == "__main__":
    main()
