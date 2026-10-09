# Changelog

## v2.1

- Install action dependencies from `uv.lock` with uv. Development and CI use the same lockfile, and Dependabot keeps it current.
- Update Black to 26.10.0, isort to 9.0.2, and charset-normalizer to 3.5.2.
- Use setup-uv v10.3.0 in the action and CI.
- Run CI once per pull-request commit while retaining checks on merges to `main`.

The action inputs, outputs, and recommendation behavior are unchanged from v2.0. Pin workflows to `gojiplus/adjacent@v2.1` to use this release.

## v2.0

Adjacent now updates only an explicitly marked README section and ranks related repositories using scores computed on a shared text corpus.

### Breaking changes

- Require one `adjacent:start` and one `adjacent:end` HTML comment around the generated section. Heading-based replacement has been removed.
- Exclude private, disabled, archived, forked, and template repositories by default. Archives, forks, and templates have individual opt-ins.
- Use raw topic and README scores instead of normalizing each component by the best candidate. Recommendations can change or become fewer.
- Keep explicit `topics` and `readme` modes within their requested signal. Only combined mode redistributes weight when the target lacks a signal.
- Replace stale recommendations with an empty-result message after a successful search with no matches.
- Run the action on Python 3.13. Development checks cover Python 3.13 and 3.14.

### Improvements

- Preserve surrounding README bytes and newline style; write changes atomically and skip unchanged content.
- Add API timeouts, bounded retries, rate-limit handling, organization discovery, pagination validation, and input validation. Failed discovery leaves the README untouched.
- Add `readme_path`, `min_score`, `include_forks`, `include_archived`, `include_templates`, and `dry_run` inputs.
- Expose `changed` and `recommendation_count` outputs and a job summary with component scores and shared topics.
- Remove generated recommendation blocks, badges, and code from text scoring, and resolve tied scores by repository name.
- Add regression tests, formatting and lint checks, Docker validation, and dependency updates.

See the README for marker setup, migration instructions, and workflow examples.
