import os
import requests

REPO = os.getenv("GITHUB_REPOSITORY")  # e.g., 'soodoku/bloomjoin'
TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}"
}

def get_topics(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/topics"
    r = requests.get(url, headers=HEADERS)
    return r.json().get("names", []) if r.status_code == 200 else []

def get_user_repos(owner):
    url = f"https://api.github.com/users/{owner}/repos?per_page=100&type=owner"
    repos = []
    while url:
        r = requests.get(url, headers=HEADERS)
        repos.extend(r.json())
        url = r.links.get("next", {}).get("url")
    return repos

def find_adjacent(owner, repo_name, topics):
    repos = get_user_repos(owner)
    related = []
    for r in repos:
        if r["name"].lower() == repo_name.lower():
            continue
        t = get_topics(r["owner"]["login"], r["name"])
        common = set(t) & set(topics)
        if common:
            related.append((r["full_name"], r.get("description", ""), list(common)))
    return sorted(related, key=lambda x: -len(x[2]))

def update_readme(related):
    with open("README.md", "r", encoding="utf-8") as f:
        lines = f.readlines()

    header = "## 🔗 Adjacent Repositories"
    start = next((i for i, l in enumerate(lines) if header in l), -1)
    block = [f"{header}\n\n"]
    for full_name, desc, tags in related[:5]:
        url = f"https://github.com/{full_name}"
        desc_str = f" — {desc}" if desc else ""
        block.append(f"- [{full_name}]({url}){desc_str}\n")

    if start >= 0:
        end = start + 1
        while end < len(lines) and lines[end].startswith("- "):
            end += 1
        lines[start:end] = block
    else:
        lines.append("\n" + "".join(block))

    with open("README.md", "w", encoding="utf-8") as f:
        f.writelines(lines)

if __name__ == "__main__":
    owner, repo = REPO.split("/")
    topics = get_topics(owner, repo)
    if not topics:
        print("No topics found.")
        exit(0)

    related = find_adjacent(owner, repo, topics)
    if related:
        update_readme(related)
        print("README updated.")
    else:
        print("No adjacent repos found.")
