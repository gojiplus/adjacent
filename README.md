# 🤝 Adjacent — Related Repositories Recommender

![GitHub release (latest by date)](https://img.shields.io/github/v/release/gojiplus/adjacent)
![GitHub Marketplace](https://img.shields.io/badge/GitHub%20Marketplace-adjacent%20Code%20Fixer-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

**Adjacent** is a GitHub Action that discovers and inserts a list of **related repositories** into your README based on shared GitHub topics.

Perfect for discovery, organization, and letting your users explore similar tools you’ve built.

---

## 🚀 Features

- 🔎 Finds related repositories by topic similarity
- 🧠 Ranks and inserts up to 5 adjacent repos into your `README.md`
- 🔄 Runs on a schedule or manual trigger
- 💬 Ideal for portfolios, developer tools, and curated ecosystems

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
        uses: gojiplus/adjacent@v1.3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}  # ✅ Pass the required token

      - name: Commit and push changes
        run: |
          git config --global user.name "github-actions"
          git config --global user.email "actions@github.com"
          git add README.md
          git commit -m "Update adjacent repositories [automated]" || echo "No changes to commit"
          git push

```

## 🔗 Adjacent Repositories

- [gojiplus/reporoulette](https://github.com/gojiplus/reporoulette) — Sample Random GitHub Repositories
