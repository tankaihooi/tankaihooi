"""Render a teal contribution-activity graph (last 31 days) as an SVG.

Replaces github-readme-activity-graph.vercel.app, whose public deployment is
disabled. Standard library only, so the workflow needs no pip install.

Usage:  GITHUB_TOKEN=... GITHUB_USER=tankaihooi python3 activity_graph.py out.svg
"""

import json
import os
import sys
import urllib.request
from datetime import date
from html import escape

DAYS = 31
W, H = 1100, 320
LEFT, RIGHT, TOP, BOTTOM = 72, 1052, 104, 262

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_days(login, token):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for week in calendar["weeks"] for d in week["contributionDays"]]
    return calendar["totalContributions"], days


def nice_max(value):
    """Round the y-axis ceiling up to an even step so gridlines land on integers."""
    for step in (4, 8, 12, 20, 40, 60, 100, 200, 400, 1000):
        if value <= step:
            return step
    return value


def render(login, year_total, days):
    recent = days[-DAYS:]
    counts = [d["contributionCount"] for d in recent]
    top = nice_max(max(counts) if counts else 0)
    span_x = (RIGHT - LEFT) / (len(recent) - 1)

    def x(i):
        return LEFT + i * span_x

    def y(v):
        return BOTTOM - (v / top) * (BOTTOM - TOP)

    points = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in points)
    area = f"{line} L{points[-1][0]:.1f} {BOTTOM} L{points[0][0]:.1f} {BOTTOM} Z"

    grid, ylabels = [], []
    for k in range(5):
        v = top * k / 4
        gy = y(v)
        grid.append(f'<path class="grid" d="M{LEFT} {gy:.1f} H{RIGHT}"/>')
        ylabels.append(f'<text x="{LEFT - 14}" y="{gy + 4:.1f}" class="axis" text-anchor="end">{v:g}</text>')

    xlabels = []
    for i, d in enumerate(recent):
        if i % 5 == 0 or i == len(recent) - 1:
            label = date.fromisoformat(d["date"]).strftime("%b %d").upper()
            xlabels.append(f'<text x="{x(i):.1f}" y="{BOTTOM + 26}" class="axis" text-anchor="middle">{label}</text>')

    dots = "".join(
        f'<circle class="pt" cx="{px:.1f}" cy="{py:.1f}" r="{4.5 if c else 2.5}"/>'
        for (px, py), c in zip(points, counts)
    )

    month_total = sum(counts)
    best = max(recent, key=lambda d: d["contributionCount"]) if recent else None
    best_label = (
        f'{best["contributionCount"]} · {date.fromisoformat(best["date"]).strftime("%b %d")}'
        if best and best["contributionCount"]
        else "—"
    )
    active = sum(1 for c in counts if c)

    stats = [
        ("LAST 31 DAYS", str(month_total)),
        ("ACTIVE DAYS", f"{active}/{len(counts)}"),
        ("BEST DAY", best_label),
        ("PAST YEAR", str(year_total)),
    ]
    stat_svg = []
    sx = RIGHT
    for label, value in reversed(stats):
        stat_svg.append(
            f'<text x="{sx}" y="46" class="statLabel" text-anchor="end">{escape(label)}</text>'
            f'<text x="{sx}" y="72" class="statValue" text-anchor="end">{escape(value)}</text>'
        )
        sx -= 190

    updated = date.today().strftime("%d %b %Y")

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Contribution activity for {escape(login)}</title>
  <desc id="desc">{month_total} contributions over the last {DAYS} days and {year_total} over the past year.</desc>
  <style>
    .title {{ font: 800 18px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; fill: #F0FDFA; letter-spacing: .08em; }}
    .sub {{ font: 600 12px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; fill: #99F6E4; }}
    .axis {{ font: 600 10px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; fill: #5EEAD4; opacity: .75; letter-spacing: .04em; }}
    .statLabel {{ font: 700 9px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; fill: #5EEAD4; letter-spacing: .14em; }}
    .statValue {{ font: 800 16px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; fill: #FFFFFF; }}
    .grid {{ stroke: #134E4A; stroke-width: 1; opacity: .7; }}
    .line {{ stroke: url(#lineGrad); stroke-width: 3; stroke-linejoin: round; stroke-linecap: round; filter: url(#glow); }}
    .pt {{ fill: #0B1220; stroke: #2DD4BF; stroke-width: 2; }}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0B1220"/>
      <stop offset=".5" stop-color="#0B1F26"/>
      <stop offset="1" stop-color="#0B1220"/>
    </linearGradient>
    <linearGradient id="lineGrad" x1="{LEFT}" y1="0" x2="{RIGHT}" y2="0" gradientUnits="userSpaceOnUse">
      <stop stop-color="#38BDF8"/>
      <stop offset=".5" stop-color="#14B8A6"/>
      <stop offset="1" stop-color="#99F6E4"/>
    </linearGradient>
    <linearGradient id="areaGrad" x1="0" y1="{TOP}" x2="0" y2="{BOTTOM}" gradientUnits="userSpaceOnUse">
      <stop stop-color="#14B8A6" stop-opacity=".45"/>
      <stop offset="1" stop-color="#14B8A6" stop-opacity="0"/>
    </linearGradient>
    <filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#14B8A6" flood-opacity=".7"/>
    </filter>
  </defs>
  <rect width="{W}" height="{H}" rx="18" fill="url(#bg)"/>
  <text x="{LEFT - 24}" y="46" class="title">CONTRIBUTION ACTIVITY</text>
  <text x="{LEFT - 24}" y="68" class="sub">Last {DAYS} days · updated {updated}</text>
  {"".join(stat_svg)}
  {"".join(grid)}
  {"".join(ylabels)}
  <path d="{area}" fill="url(#areaGrad)"/>
  <path class="line" d="{line}"/>
  {dots}
  {"".join(xlabels)}
</svg>
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "activity.svg"
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ.get("GITHUB_USER") or os.environ["GITHUB_REPOSITORY_OWNER"]
    year_total, days = fetch_days(login, token)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(login, year_total, days))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
