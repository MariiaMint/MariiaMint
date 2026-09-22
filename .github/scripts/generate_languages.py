#!/usr/bin/env python3
import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.getenv("GITHUB_USERNAME", "MariiaMint")
OUTPUT = Path(os.getenv("OUTPUT_FILE", "languages.svg"))
TOKEN = os.getenv("GITHUB_TOKEN", "")
INCLUDE_FORKS = os.getenv("INCLUDE_FORKS", "false").lower() == "true"

COLORS = {
    "Kotlin": "#A97BFF",
    "Java": "#B07219",
    "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A",
    "Python": "#3572A5",
    "HTML": "#E34C26",
    "CSS": "#563D7C",
    "SCSS": "#C6538C",
    "SQL": "#E38C00",
    "Shell": "#89E051",
    "C": "#555555",
    "C++": "#F34B7D",
    "C#": "#178600",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "Dart": "#00B4AB",
    "Swift": "#F05138",
    "PHP": "#4F5D95",
    "Ruby": "#701516",
    "Vue": "#41B883",
    "Dockerfile": "#384D54",
    "PowerShell": "#012456",
    "Jupyter Notebook": "#DA5B0B",
}
FALLBACK = "#8B949E"


def github_get(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "MariiaMint-profile-language-card",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def get_repositories():
    repositories = []
    page = 1

    while True:
        params = urllib.parse.urlencode({
            "type": "owner",
            "per_page": 100,
            "page": page,
        })
        url = f"https://api.github.com/users/{urllib.parse.quote(USERNAME)}/repos?{params}"
        batch = github_get(url)

        if not batch:
            break

        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    return repositories


def collect_languages(repositories):
    totals = defaultdict(int)
    counted_repositories = 0

    for repo in repositories:
        if repo.get("archived"):
            continue
        if repo.get("fork") and not INCLUDE_FORKS:
            continue

        counted_repositories += 1
        languages = github_get(repo["languages_url"])

        for language, byte_count in languages.items():
            totals[language] += int(byte_count)

    return sorted(totals.items(), key=lambda item: (-item[1], item[0])), counted_repositories


def format_bytes(value):
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def make_svg(items, repository_count):
    width = 900
    row_height = 46
    header_height = 112
    bottom = 28
    height = header_height + max(1, len(items)) * row_height + bottom

    total_bytes = sum(value for _, value in items) or 1
    max_value = max((value for _, value in items), default=1)

    rows = []
    for index, (language, value) in enumerate(items):
        y = header_height + index * row_height
        percent = value / total_bytes * 100
        bar_width = max(4, 530 * value / max_value)
        color = COLORS.get(language, FALLBACK)

        rows.append(f'''\
  <g transform="translate(0 {y})">
    <circle cx="28" cy="18" r="6" fill="{color}"/>
    <text x="48" y="23" class="lang">{escape(language)}</text>
    <rect x="235" y="8" width="530" height="18" rx="9" fill="#21262D"/>
    <rect x="235" y="8" width="{bar_width:.1f}" height="18" rx="9" fill="{color}"/>
    <text x="790" y="22" class="percent">{percent:.1f}%</text>
    <text x="855" y="22" class="bytes">{format_bytes(value)}</text>
  </g>''')

    if not items:
        rows.append('''\
  <text x="40" y="145" class="empty">No languages detected yet.</text>''')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Languages used across public repositories of {escape(USERNAME)}">
  <rect width="100%" height="100%" rx="24" fill="#0D1117"/>
  <rect x="1" y="1" width="898" height="{height - 2}" rx="23" fill="none" stroke="#30363D"/>
  <style>
    .title {{ font: 700 25px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #F0F6FC; }}
    .subtitle {{ font: 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #8B949E; }}
    .lang {{ font: 600 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #E6EDF3; }}
    .percent {{ font: 600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #C9D1D9; text-anchor: end; }}
    .bytes {{ font: 12px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #8B949E; text-anchor: end; }}
    .empty {{ font: 14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; fill: #8B949E; }}
  </style>
  <text x="32" y="42" class="title">✨ Languages across my repositories</text>
  <text x="32" y="68" class="subtitle">GitHub Linguist · {repository_count} public repositories · all detected languages</text>
  <text x="32" y="91" class="subtitle">Updated automatically by GitHub Actions</text>
{chr(10).join(rows)}
</svg>
'''


def main():
    repositories = get_repositories()
    items, repository_count = collect_languages(repositories)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(make_svg(items, repository_count), encoding="utf-8")

    print(f"Repositories scanned: {repository_count}")
    print("Languages:")
    for language, byte_count in items:
        print(f"  {language}: {byte_count} bytes")
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
