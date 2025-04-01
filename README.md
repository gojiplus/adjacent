# 🤝 Adjacent — Related Repositories Recommender

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

### 1. **Add to your workflow**

Save the following to `.github/workflows/adjacent.yml`:

```yaml
name: Adjacent Recommender

on:
  workflow_dispatch:
    inputs:
      repo:
        description: 'Target repo (owner/name)'
        required: true
  schedule:
    - cron: '0 5 * * 0'  # every Sunday

jobs:
  update-adjacent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: your-username/adjacent@v1
        with:
          repo: ${{ github.event.inputs.repo }}

```

## 🔗 Adjacent Repositories

- [gojiplus/reporoulette](https://github.com/gojiplus/reporoulette) — Sample Random GitHub Repositories

- [gojiplus/reporoulette](https://github.com/gojiplus/reporoulette) — Sample Random GitHub Repositories
