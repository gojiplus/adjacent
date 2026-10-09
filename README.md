# Adjacent

[![Release](https://img.shields.io/github/v/release/gojiplus/adjacent)](https://github.com/gojiplus/adjacent/releases)
[![CI](https://github.com/gojiplus/adjacent/actions/workflows/ci.yml/badge.svg)](https://github.com/gojiplus/adjacent/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Used By](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/gojiplus/adjacent/main/docs/adjacent.json)](https://github.com/search?q=gojiplus/adjacent+path%3A.github%2Fworkflows+language%3AYAML&type=code)

Adjacent is a GitHub Action that adds related repositories to your README. It compares topics and README text across public repositories owned by the same user or organization. Use it to help readers discover related projects in your portfolio or ecosystem.

Adjacent edits only the section you mark. It preserves the rest of the file, leaves the README untouched if discovery fails, and reports the scores behind each recommendation in the workflow summary. It runs without a paid API or language model.

## Setup

Version 2 requires explicit README markers. When upgrading from version 1, follow the migration instructions below before enabling writes.

### Mark the section

Add one start comment and one end comment to an existing README, each on its own line:

<pre>&lt;!-- adjacent:start --&gt;

&lt;!-- adjacent:end --&gt;</pre>

Adjacent replaces everything between these comments. Put any heading you want it to manage inside the markers. Missing, repeated, or reversed markers stop the action before discovery. The README must already exist inside the checkout.

### Add a workflow

Save this as `.github/workflows/adjacent.yml`:

```yaml
name: Related repositories
on:
  schedule:
    - cron: '0 5 * * 0'
  workflow_dispatch:
permissions:
  contents: write
concurrency:
  group: adjacent-${{ github.ref }}
  cancel-in-progress: false
jobs:
  recommend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7.0.1
      - uses: gojiplus/adjacent@v2.1
        id: adjacent
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - name: Commit changes
        if: steps.adjacent.outputs.changed == 'true'
        run: |
          git config user.name 'github-actions[bot]'
          git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
          git add README.md
          if ! git diff --cached --quiet; then
            git commit -m 'Update adjacent repositories'
            git push
          fi
```

The action fetches data and edits the local file. The caller owns committing and pushing. Use `contents: read` and omit the commit step for a preview or artifact-only workflow; branch protection may require your own pull-request workflow instead of a direct push. If you change `readme_path`, change the path in `git add` too.

Set `dry_run: 'true'` and omit the commit step to preview the proposed README in the job log without changing it. Discovery still uses the GitHub API.

An existing user of Adjacent is [fox_news_transcripts](https://github.com/notnews/fox_news_transcripts/).

## Inputs and outputs

| Input | Default | Meaning |
| --- | --- | --- |
| `token` | Required | Token for GitHub API access; usually `secrets.GITHUB_TOKEN`. |
| `repo` | Current repository | Target in `owner/name` form. Candidate repositories belong to this owner. |
| `similarity_method` | `combined` | `topics`, `readme`, or `combined`. |
| `topic_weight` | `0.6` | Topic share in combined mode, from 0 to 1. |
| `exclude_repos` | Empty | Comma-separated short names or `owner/name`; case-insensitive. |
| `max_repos` | `5` | Positive integer limiting displayed recommendations. |
| `readme_path` | `README.md` | Existing marked file within the checkout. |
| `min_score` | `0.1` | Only scores strictly above this threshold qualify; from 0 to 1. |
| `include_forks` | `false` | Allow public forks. |
| `include_archived` | `false` | Allow public archived repositories. |
| `include_templates` | `false` | Allow public template repositories. |
| `dry_run` | `false` | Compute and display proposed content without writing. |

Boolean inputs accept `true` and `false`. Private and disabled repositories, the target itself, and explicit exclusions are always omitted. An opt-in changes only its corresponding filter: an archived fork needs both opt-ins.

| Output | Meaning |
| --- | --- |
| `changed` | `true` when proposed content differs from the local README, including during dry runs. |
| `recommendation_count` | Number of selected recommendations after thresholding and truncation. |

The job summary reports total scores, topic scores, README scores, and shared topics. A successful search with no qualifying results replaces stale recommendations with “No related repositories found.”

## How ranking works

Topic similarity is the fraction of distinct topics shared by the two repositories: the intersection divided by the union. README similarity uses cosine similarity from one TF-IDF model fitted across the target and eligible candidates. TF-IDF gives less weight to terms common across that collection. Generated Adjacent sections, images, badges, and code are removed before scoring; useful link text stays.

Combined mode uses `topic_weight × topic_score + (1 − topic_weight) × readme_score`. If the target has no topics or no usable README text, the available signal receives all the weight. A candidate missing a signal gets zero for that component. Explicit `topics` and `readme` modes use only the requested signal. If neither signal is available, no repositories qualify. English stop words are removed; text similarity is not a semantic or multilingual model.

Scores are not probabilities and are not rescaled to make the best candidate score 1. Changing the candidate collection can change TF-IDF scores. Equal scores are ordered by repository name, so identical API data produces identical output. README text comes from GitHub's default-branch README, even if `readme_path` points to another local file.

API calls have timeouts and up to three retries for transient failures. Rate-limit waits honor GitHub headers; waits over five minutes fail with a retry-later message. Missing READMEs contribute no text. Authentication errors, malformed responses, and exhausted retries fail the run without modifying the README.

## Migrating from earlier releases

Wrap the existing generated section, including its heading and attribution, in the marker pair shown above. Keep manually written content outside it. Heading-based replacement and automatic method fallback have been removed.

Review recommendations with `dry_run` before enabling writes. Default filtering now excludes archives, forks, and templates, and raw scoring can produce fewer recommendations than earlier versions. Use the opt-ins or adjust `min_score` if needed. The action runs Python 3.13; development checks also cover Python 3.14.

## Development

```sh
uv sync
make check
```

Install [actionlint](https://github.com/rhysd/actionlint) for workflow checks. `make check` runs Black, isort, flake8, pytest, and actionlint; `make format` applies Python formatting. Tests mock GitHub and do not need a token.

With Docker running:

```sh
make ci-docker
make ci-docker PYTHON_VERSION=3.14
```

These commands use standard Python images and the upstream actionlint image, with the checkout mounted read-only. CI runs the same Python checks for both supported versions.

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`, which the action installs with `uv run --locked`. Refresh the lock with `uv lock --upgrade`.

For a read-only live smoke test, export `GITHUB_TOKEN` through your normal credential setup, then run from this checkout:

```sh
GITHUB_REPOSITORY=gojiplus/adjacent SIMILARITY_METHOD=topics DRY_RUN=true uv run python -m adjacent
```

The entrypoint reads the uppercase equivalents of action inputs, except `repo` and `token`, which use `GITHUB_REPOSITORY` and `GITHUB_TOKEN`. `GITHUB_WORKSPACE` sets the checkout root; it defaults to the current directory. This internal module is run directly from the action checkout and is not published as a Python package.

<!-- adjacent:start -->

## 🔗 Adjacent Repositories

- [gojiplus/reporoulette](https://github.com/gojiplus/reporoulette) — Sample Random GitHub Repositories

_Powered by [Adjacent](https://github.com/gojiplus/adjacent)_

<!-- adjacent:end -->
