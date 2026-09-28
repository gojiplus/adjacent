import math
import re
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_PATTERN = r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+"


def valid_repository(value):
    return (
        isinstance(value, str)
        and re.fullmatch(REPOSITORY_PATTERN, value) is not None
        and value.split("/")[1] not in {".", ".."}
    )


@dataclass(frozen=True)
class Config:
    repo: str
    token: str
    path: Path
    method: str
    weight: float
    limit: int
    threshold: float
    exclusions: frozenset[str]
    include_forks: bool
    include_archived: bool
    include_templates: bool
    dry_run: bool

    @classmethod
    def from_env(cls, env):
        repo = env.get("GITHUB_REPOSITORY", "")
        if not valid_repository(repo):
            raise ValueError("GITHUB_REPOSITORY must be owner/name")
        token = env.get("GITHUB_TOKEN", "").strip()
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        method = env.get("SIMILARITY_METHOD", "combined")
        if method not in {"topics", "readme", "combined"}:
            raise ValueError("SIMILARITY_METHOD must be topics, readme, or combined")

        def unit(name, default):
            value = float(env.get(name, default))
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and in [0, 1]")
            return value

        def boolean(name):
            value = env.get(name, "false").lower()
            if value not in {"true", "false"}:
                raise ValueError(f"{name} must be true or false")
            return value == "true"

        limit = int(env.get("MAX_REPOS", "5"))
        if limit <= 0:
            raise ValueError("MAX_REPOS must be positive")
        root = Path(env.get("GITHUB_WORKSPACE", ".")).resolve()
        path = (root / env.get("README_PATH", "README.md")).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("README_PATH must be an existing file within the checkout")
        return cls(
            repo,
            token,
            path,
            method,
            unit("TOPIC_WEIGHT", "0.6"),
            limit,
            unit("MIN_SCORE", "0.1"),
            frozenset(
                x.strip().casefold()
                for x in env.get("EXCLUDE_REPOS", "").split(",")
                if x.strip()
            ),
            boolean("INCLUDE_FORKS"),
            boolean("INCLUDE_ARCHIVED"),
            boolean("INCLUDE_TEMPLATES"),
            boolean("DRY_RUN"),
        )
