import logging
import os
import sys
from pathlib import Path

from adjacent.config import Config
from adjacent.github import GitHub, GitHubError
from adjacent.ranking import eligible, rank
from adjacent.render import bounds, escape, render, write_atomic


def run(env=None, client=None):
    env = os.environ if env is None else env
    config = Config.from_env(env)
    original = config.path.read_bytes()
    bounds(original)
    client = client or GitHub(config.token)
    target = client.repository(config.repo)
    candidates = sorted(
        {
            r["full_name"]: r
            for r in client.repositories(
                config.repo.split("/")[0], target["owner"]["type"]
            )
            if eligible(r, config)
        }.values(),
        key=lambda r: r["full_name"],
    )
    readmes = {}
    if config.method != "topics" and (
        config.method == "readme" or config.weight < 1 or not target["topics"]
    ):
        readmes[target["full_name"]] = client.readme(target["full_name"])
        if readmes[target["full_name"]]:
            for repo in candidates:
                readmes[repo["full_name"]] = client.readme(repo["full_name"])
    recommendations = rank(target, candidates, readmes, config)
    updated = render(original, recommendations)
    changed = updated != original
    if changed and not config.dry_run:
        write_atomic(config.path, updated)
    summary = [
        f"Adjacent: {len(recommendations)} recommendations; "
        f"changed={str(changed).lower()}; dry_run={str(config.dry_run).lower()}",
        "",
        "| Repository | Score | Topics | README | Shared topics |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for item in recommendations:
        summary.append(
            f"| {item.full_name} | {item.score:.4f} | {item.topic_score:.4f} "
            f"| {item.readme_score:.4f} | {escape(', '.join(item.topics))} |"
        )
    text = "\n".join(summary) + "\n"
    print(text)
    if config.dry_run:
        print(updated.decode("utf-8"))
    if env.get("GITHUB_STEP_SUMMARY"):
        with Path(env["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
            stream.write(text)
    if env.get("GITHUB_OUTPUT"):
        with Path(env["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            stream.write(
                f"changed={str(changed).lower()}\n"
                f"recommendation_count={len(recommendations)}\n"
            )
    return recommendations


def main():
    try:
        run()
    except (ValueError, OSError, GitHubError) as error:
        logging.error("%s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
