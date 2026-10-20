"""Gera os cards de estatísticas do perfil (assets/stats.svg e assets/langs.svg).

Roda no GitHub Actions (.github/workflows/stats.yml) com o GITHUB_TOKEN.
Conta só repositórios públicos do perfil, sem forks e sem o próprio repositório do README.
"""
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GITHUB_USER", "soares-dev7")
IGNORE = {USER}  # o repositório do README não entra na conta
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    contributionsCollection { totalCommitContributions restrictedContributionsCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

STYLE = """<style>
  .bg { fill: #ffffff; stroke: #d0d7de; }
  .title { fill: #0969da; font: 600 16px 'Segoe UI', Ubuntu, sans-serif; }
  .label { fill: #57606a; font: 400 13px 'Segoe UI', Ubuntu, sans-serif; }
  .value { fill: #1f2328; font: 700 13px 'Segoe UI', Ubuntu, sans-serif; }
  .track { fill: #eaeef2; }
  @media (prefers-color-scheme: dark) {
    .bg { fill: #0d1117; stroke: #30363d; }
    .title { fill: #58a6ff; }
    .label { fill: #8b949e; }
    .value { fill: #e6edf3; }
    .track { fill: #21262d; }
  }
</style>"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if "errors" in data:
        sys.exit(f"Erro na API do GitHub: {data['errors']}")
    return data["data"]["user"]


def summarize(user):
    repos = [r for r in user["repositories"]["nodes"] if r["name"] not in IGNORE]
    languages = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            total, color = languages.get(name, (0, edge["node"]["color"] or "#8b949e"))
            languages[name] = (total + edge["size"], color)
    contributions = user["contributionsCollection"]
    stats = [
        ("Public repositories", len(repos)),
        ("Commits (last year)", contributions["totalCommitContributions"] + contributions["restrictedContributionsCount"]),
        ("Pull requests", user["pullRequests"]["totalCount"]),
        ("Stars earned", sum(r["stargazerCount"] for r in repos)),
        ("Followers", user["followers"]["totalCount"]),
    ]
    return stats, sorted(languages.items(), key=lambda item: -item[1][0])[:6]


def stats_svg(stats):
    height = 65 + len(stats) * 25
    rows = "".join(
        f'<text class="label" x="25" y="{70 + i * 25}">{escape(label)}</text>'
        f'<text class="value" x="300" y="{70 + i * 25}" text-anchor="end">{value}</text>'
        for i, (label, value) in enumerate(stats)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="325" height="{height}" viewBox="0 0 325 {height}" role="img" aria-label="GitHub stats">'
        f'{STYLE}<rect class="bg" x="0.5" y="0.5" width="324" height="{height - 1}" rx="6"/>'
        f'<text class="title" x="25" y="35">GitHub stats</text>{rows}</svg>'
    )


def langs_svg(languages):
    total = sum(size for _, (size, _) in languages) or 1
    height = 70 + ((len(languages) + 1) // 2) * 25
    bar, x = [], 25
    for name, (size, color) in languages:
        width = 275 * size / total
        bar.append(f'<rect x="{x:.2f}" y="50" width="{width:.2f}" height="8" fill="{color}"/>')
        x += width
    items = []
    for i, (name, (size, color)) in enumerate(languages):
        cx, cy = 25 + (i % 2) * 140, 85 + (i // 2) * 25
        items.append(
            f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{color}"/>'
            f'<text class="label" x="{cx + 16}" y="{cy}">{escape(name)} <tspan class="value">{100 * size / total:.1f}%</tspan></text>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="325" height="{height}" viewBox="0 0 325 {height}" role="img" aria-label="Most used languages">'
        f'{STYLE}<rect class="bg" x="0.5" y="0.5" width="324" height="{height - 1}" rx="6"/>'
        f'<text class="title" x="25" y="35">Most used languages</text>'
        f'<clipPath id="bar"><rect x="25" y="50" width="275" height="8" rx="4"/></clipPath>'
        f'<rect class="track" x="25" y="50" width="275" height="8" rx="4"/><g clip-path="url(#bar)">{"".join(bar)}</g>'
        f'{"".join(items)}</svg>'
    )


def main():
    stats, languages = summarize(fetch())
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "stats.svg"), "w", encoding="utf-8") as file:
        file.write(stats_svg(stats))
    with open(os.path.join(OUT, "langs.svg"), "w", encoding="utf-8") as file:
        file.write(langs_svg(languages))
    print(stats, [name for name, _ in languages])


if __name__ == "__main__":
    main()
