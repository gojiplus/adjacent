from dataclasses import replace
from pathlib import Path

import pytest

from adjacent.config import Config
from adjacent.ranking import Recommendation, eligible
from adjacent.render import END, START, bounds, render, write_atomic
from tests.conftest import MARKED, repository


@pytest.mark.parametrize(
    "key,value",
    [
        ("GITHUB_REPOSITORY", "invalid"),
        ("GITHUB_TOKEN", ""),
        ("SIMILARITY_METHOD", "magic"),
        ("TOPIC_WEIGHT", "nan"),
        ("TOPIC_WEIGHT", "inf"),
        ("TOPIC_WEIGHT", "-1"),
        ("MIN_SCORE", "1.1"),
        ("MAX_REPOS", "0"),
        ("MAX_REPOS", "2.5"),
        ("INCLUDE_FORKS", "yes"),
        ("INCLUDE_ARCHIVED", "1"),
        ("INCLUDE_TEMPLATES", "maybe"),
        ("DRY_RUN", "sometimes"),
        ("README_PATH", "../outside.md"),
        ("README_PATH", "missing.md"),
    ],
)
def test_invalid_config(env, key, value):
    with pytest.raises(ValueError):
        Config.from_env(env | {key: value})


def test_config_defaults_and_symlink_escape(env, tmp_path):
    config = Config.from_env(env)
    assert (config.method, config.weight, config.limit, config.threshold) == (
        "combined",
        0.6,
        5,
        0.1,
    )
    (tmp_path / "escape").symlink_to("/etc/hosts")
    with pytest.raises(ValueError):
        Config.from_env(env | {"README_PATH": "escape"})


@pytest.mark.parametrize(
    "data", [b"", START, END, END + START, START + START + END, START + END + END]
)
def test_bad_markers(data):
    with pytest.raises(ValueError):
        bounds(data)


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_preservation_idempotence_and_escape(tmp_path, newline):
    original = MARKED.replace(b"\n", newline)
    item = Recommendation(
        "owner/tool", "[link](evil)\n<script>x</script> | *bold*", (), 1, 0, 1
    )
    updated = render(original, [item])
    before, after = bounds(original)
    assert updated[:before] == original[:before]
    assert updated.endswith(original[after:])
    assert b"Keep me." in updated
    assert b"<script>" not in updated
    assert b"\\[link\\]" in updated and b"\\|" in updated
    assert render(updated, [item]) == updated
    if newline == b"\r\n":
        assert b"\n" not in updated.replace(b"\r\n", b"")
    path = tmp_path / "README.md"
    path.write_bytes(original)
    path.chmod(0o640)
    write_atomic(path, updated)
    assert path.read_bytes() == updated
    assert path.stat().st_mode & 0o777 == 0o640
    assert list(tmp_path.iterdir()) == [path]


def test_empty_result_replaces_stale_content():
    updated = render(MARKED, [])
    assert b"No related repositories found." in updated
    assert b"old" not in updated


@pytest.mark.parametrize(
    "field", ["private", "disabled", "fork", "archived", "is_template"]
)
def test_filters(env, field):
    config = Config.from_env(env)
    repo = repository("owner/other", **{field: True})
    assert not eligible(repo, config)
    option = {
        "fork": "include_forks",
        "archived": "include_archived",
        "is_template": "include_templates",
    }.get(field)
    if option:
        assert eligible(repo, replace(config, **{option: True}))


def test_exclusions(env):
    config = Config.from_env(env | {"EXCLUDE_REPOS": " OTHER, owner/third "})
    for name in ("owner/other", "owner/THIRD", "OWNER/TARGET", "elsewhere/tool"):
        assert not eligible(repository(name), config)
    assert eligible(repository("owner/valid"), config)


def test_absolute_path_within_checkout(env):
    path = Path(env["GITHUB_WORKSPACE"]) / "README.md"
    assert Config.from_env(env | {"README_PATH": str(path)}).path == path
