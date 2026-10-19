import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode

from adjacent.github import GitHub, GitHubError

ACTIONS = (
    "gojiplus/adjacent",
    "recite/retract",
    "matmulai/auto-pr",
    "gojiplus/allstar",
    "recite/citation-sync",
)


def update_counts(github, directory, actions=ACTIONS, sleep=time.sleep):
    counts = {}
    for index, action in enumerate(actions):
        if index:
            sleep(65)
        query = action.replace("/", " ") + " path:.github/workflows language:YAML"
        data = github.json(github.get("/search/code?" + urlencode({"q": query})))
        count = data.get("total_count")
        if type(count) is not int or count < 0 or data.get("incomplete_results"):
            raise GitHubError("GitHub returned an incomplete or invalid action count")
        message = str(count) if count < 10000 else f"{count // 100 * 100 / 1000:.1f}K"
        if count >= 1000000:
            message = f"{count // 10000 * 10000 / 1000000:.2f}M"
        counts[action.split("/")[1]] = {
            "schemaVersion": 1,
            "label": "used by",
            "message": message,
            "color": "#007ec6",
            "namedLogo": "githubactions",
            "logoColor": "#fff",
            "style": "flat",
        }
    directory.mkdir(parents=True, exist_ok=True)
    for name, badge in counts.items():
        (directory / f"{name}.json").write_text(
            json.dumps(badge, sort_keys=True) + "\n"
        )


if __name__ == "__main__":
    try:
        update_counts(GitHub(os.environ["GITHUB_TOKEN"]), Path("docs"))
    except GitHubError as exc:
        raise SystemExit(str(exc)) from None
