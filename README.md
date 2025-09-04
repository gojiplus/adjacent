# 🤝 Adjacent — Related Repositories Recommender

![GitHub release (latest by date)](https://img.shields.io/github/v/release/gojiplus/adjacent)
![GitHub Marketplace](https://img.shields.io/badge/GitHub%20Marketplace-adjacent)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
[![Used By](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/gojiplus/adjacent/main/docs/adjacent.json)](https://github.com/search?q=gojiplus/adjacent+path%3A.github%2Fworkflows+language%3AYAML&type=code)

**Adjacent** is a GitHub Action that discovers and inserts a list of **related repositories** into your README based on shared GitHub topics and README content similarity.

Perfect for discovery, organization, and letting your users explore similar tools you've built.

---

## 🚀 Features

- 🔎 **Multiple similarity methods**: GitHub topics, README content, or combined approach
- 🧠 **Smart ranking**: Configurable weighting between topics and content similarity
- 🚫 **Repository exclusions**: Skip specific repositories you don't want to include
- 📊 **Customizable output**: Set maximum number of repositories to display
- 🔄 **Automated updates**: Runs on schedule or manual trigger
- 💬 **Perfect for**: Portfolios, developer tools, and curated ecosystems

---

## 📦 Usage

Here's a repository that uses this GitHub Action: https://github.com/notnews/fox_news_transcripts/

### 1. **Add to your workflow**

Save the following to `.github/workflows/adjacent.yml`:

```yaml
name: Find Adjacent Repositories

on:
  schedule:
    - cron: '0 5 * * 0'   # Every Sunday at 5am UTC
  workflow_dispatch:

jobs:
  recommend-repos:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Adjacent Repositories Recommender
        uses: gojiplus/adjacent@v1.4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}  # ✅ Required: GitHub token
          similarity_method: 'combined'        # Optional: topics, readme, or combined
          topic_weight: '0.6'                  # Optional: weight for topics (0-1)
          exclude_repos: 'template,archived'   # Optional: comma-separated exclusions
          max_repos: '5'                       # Optional: max repositories to show

      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions"
          git config --global user.email "actions@github.com"
          git add README.md
          git commit -m "Update adjacent repositories [automated]" || echo "No changes to commit"
          git push

```

## ⚙️ Configuration Options

| Input | Description | Default | Example |
|-------|-------------|---------|----------|
| `token` | GitHub token for API access | **Required** | `${{ secrets.GITHUB_TOKEN }}` |
| `repo` | Target repository | Current repo | `owner/repository` |
| `similarity_method` | Method: `topics`, `readme`, or `combined` | `combined` | `topics` |
| `topic_weight` | Weight for topics in combined method (0-1) | `0.6` | `0.8` |
| `exclude_repos` | Comma-separated repository names to exclude | _(none)_ | `template,archived,old-project` |
| `max_repos` | Maximum repositories to display | `5` | `3` |

## 🔗 Adjacent Repositories

- [gojiplus/reporoulette](https://github.com/gojiplus/reporoulette) — Sample Random GitHub Repositories

✨ _Powered by [Adjacent](https://github.com/gojiplus/adjacent)_ 🚀
