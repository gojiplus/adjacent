import base64

import pytest
import responses

BASE = "https://api.github.com"
MARKED = (
    b"# Project\n\n<!-- adjacent:start -->\nold\n"
    b"<!-- adjacent:end -->\n\n# License\nKeep me.\n"
)


def repository(name="owner/target", topics=None, **fields):
    data = {
        "full_name": name,
        "owner": {"type": "User"},
        "topics": ["python"] if topics is None else topics,
        "description": "Useful software",
        "private": False,
        "disabled": False,
        "archived": False,
        "fork": False,
        "is_template": False,
    }
    return data | fields


def readme_response(name, text):
    responses.get(
        f"{BASE}/repos/{name}/readme",
        json={
            "encoding": "base64",
            "content": base64.b64encode(text.encode()).decode(),
        },
    )


@pytest.fixture
def env(tmp_path):
    (tmp_path / "README.md").write_bytes(MARKED)
    return {
        "GITHUB_REPOSITORY": "owner/target",
        "GITHUB_TOKEN": "test-token",
        "GITHUB_WORKSPACE": str(tmp_path),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }
