import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class Recommendation:
    full_name: str
    description: str
    topics: tuple[str, ...]
    topic_score: float
    readme_score: float
    score: float


def clean_markdown(text):
    text = re.sub(
        r"<!-- adjacent:start -->.*?<!-- adjacent:end -->", "", text, flags=re.S
    )
    text = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)|!\[[^\]]*\]\[[^\]]*\]", "", text)
    text = re.sub(
        r"\[([^\]]*)\]\([^)]*\)|\[([^\]]*)\]\[[^\]]*\]",
        lambda m: m[1] or m[2] or "",
        text,
    )
    text = re.sub(r"^\s*\[[^\]]+\]:.*$", "", text, flags=re.M)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def eligible(repo, config):
    name = repo["full_name"].casefold()
    return (
        name.split("/")[0] == config.repo.split("/")[0].casefold()
        and name != config.repo.casefold()
        and name not in config.exclusions
        and name.split("/")[-1] not in config.exclusions
        and not repo["private"]
        and not repo["disabled"]
        and (config.include_archived or not repo["archived"])
        and (config.include_forks or not repo["fork"])
        and (config.include_templates or not repo["is_template"])
    )


def rank(target, candidates, readmes, config):
    target_text = clean_markdown(readmes.get(target["full_name"], ""))
    scores = [0.0] * len(candidates)
    has_readme = False
    if config.method != "topics" and candidates:
        corpus = [target_text] + [
            clean_markdown(readmes.get(r["full_name"], "")) for r in candidates
        ]
        vectorizer = TfidfVectorizer(stop_words="english")
        if any(vectorizer.build_analyzer()(text) for text in corpus):
            matrix = vectorizer.fit_transform(corpus)
            has_readme = matrix[0].nnz > 0
            scores = cosine_similarity(matrix[0:1], matrix[1:]).ravel().tolist()
    topics = set(target["topics"])
    weight = config.weight
    if config.method == "topics":
        weight = 1.0
    elif config.method == "readme":
        weight = 0.0
    elif not topics:
        weight = 0.0
    elif not has_readme:
        weight = 1.0
    results = []
    for repo, readme_score in zip(candidates, scores):
        readme_score = min(1.0, max(0.0, readme_score))
        other = set(repo["topics"])
        common = topics & other
        topic_score = len(common) / len(topics | other) if topics | other else 0.0
        score = weight * topic_score + (1 - weight) * readme_score
        if score > config.threshold:
            results.append(
                Recommendation(
                    repo["full_name"],
                    repo.get("description") or "",
                    tuple(sorted(common)),
                    topic_score,
                    readme_score,
                    score,
                )
            )
    return sorted(
        results, key=lambda r: (-r.score, r.full_name.casefold(), r.full_name)
    )[: config.limit]
