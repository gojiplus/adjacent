from dataclasses import replace

import numpy as np
import pytest

from adjacent.config import Config
from adjacent.ranking import clean_markdown, rank
from tests.conftest import repository


def test_cleaning():
    text = """![build status](badge.svg) [![coverage](badge)](report)
[useful documentation](guide) ![other badge][badge]
[badge]: https://example.com
```python
irrelevant_code
```
<!-- adjacent:start -->
contaminating recommendations
<!-- adjacent:end -->
"""
    cleaned = clean_markdown(text)
    assert "useful documentation" in cleaned
    for noise in (
        "build status",
        "coverage",
        "other badge",
        "irrelevant_code",
        "contaminating",
        "example.com",
    ):
        assert noise not in cleaned


def test_relevant_outweighs_unrelated(env):
    config = Config.from_env(env | {"SIMILARITY_METHOD": "readme", "MIN_SCORE": "0"})
    target = repository()
    good, bad = repository("owner/good"), repository("owner/bad")
    results = rank(
        target,
        [bad, good],
        {
            target["full_name"]: "statistical regression modeling inference",
            good["full_name"]: "statistical regression inference models",
            bad["full_name"]: "gardening flowers soil tulips",
        },
        config,
    )
    assert [r.full_name for r in results] == ["owner/good"]


def test_weak_match_not_normalized(env, monkeypatch):
    monkeypatch.setattr(
        "adjacent.ranking.cosine_similarity", lambda *_: np.array([[0.001]])
    )
    config = Config.from_env(env)
    target, other = repository(topics=[]), repository("owner/other", topics=[])
    assert (
        rank(target, [other], {"owner/target": "text", "owner/other": "text"}, config)
        == []
    )
    results = rank(
        target,
        [other],
        {"owner/target": "text", "owner/other": "text"},
        replace(config, threshold=0),
    )
    assert results[0].score == 0.001


@pytest.mark.parametrize("method", ["readme", "combined"])
def test_empty_vocabulary(env, method):
    config = Config.from_env(env | {"SIMILARITY_METHOD": method})
    results = rank(
        repository(topics=[]),
        [repository("owner/other", topics=[])],
        {"owner/target": "the a and", "owner/other": "a and"},
        config,
    )
    assert results == []


def test_missing_signals_and_explicit_modes(env):
    config = Config.from_env(env)
    target, other = repository(), repository("owner/other")
    assert rank(target, [other], {}, config)[0].score == 1
    assert rank(target, [other], {}, replace(config, method="readme")) == []
    text = {
        "owner/target": "regression statistics",
        "owner/other": "regression statistics",
    }
    target = repository(topics=[])
    assert rank(target, [other], text, config)[0].score == pytest.approx(1)
    assert rank(target, [other], text, replace(config, method="topics")) == []


@pytest.mark.parametrize("weight,expected", [(0, 0), (1, 1), (0.6, 0.6)])
def test_weight_endpoints(env, weight, expected):
    config = replace(Config.from_env(env), weight=weight, threshold=0)
    results = rank(
        repository(),
        [repository("owner/other")],
        {"owner/target": "regression", "owner/other": "gardening"},
        config,
    )
    if expected:
        assert results[0].score == expected
    else:
        assert results == []


def test_stable_ties_and_limit(env):
    config = replace(Config.from_env(env), method="topics", limit=1)
    repos = [repository("owner/z"), repository("owner/a")]
    assert rank(repository(), repos, {}, config)[0].full_name == "owner/a"
    assert (
        rank(repository(), list(reversed(repos)), {}, config)[0].full_name == "owner/a"
    )


def test_strict_threshold(env):
    config = replace(Config.from_env(env), method="topics", threshold=1)
    assert rank(repository(), [repository("owner/other")], {}, config) == []


def test_floating_point_overshoot_does_not_pass_threshold_one(env, monkeypatch):
    monkeypatch.setattr(
        "adjacent.ranking.cosine_similarity",
        lambda *_: np.array([[1.0000000000000002]]),
    )
    config = replace(Config.from_env(env), method="readme", threshold=1)
    text = {"owner/target": "statistics", "owner/other": "statistics"}
    assert rank(repository(), [repository("owner/other")], text, config) == []


def test_missing_candidate_signal_is_not_reweighted(env):
    results = rank(
        repository(),
        [repository("owner/other")],
        {"owner/target": "statistics"},
        Config.from_env(env),
    )
    assert results[0].score == 0.6
