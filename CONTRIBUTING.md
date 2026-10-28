# Contributing

1. Branch off `main`: `fix/short-slug` for repairs, `feature/short-slug` for additions.
2. Edit the skill under `skills/social-explainer-reel/`.
3. Run the tests: `python3 -m pytest -q skills/social-explainer-reel/tests/`.
4. Rebuild the archive: `python3 tools/package_skill.py`, and commit `dist/social-explainer-reel.skill` with your change.
5. Add a line to `CHANGELOG.md`. Bump `metadata.version` in `SKILL.md` for user-visible changes.

## Skill rules

- `SKILL.md` addresses the agent. Keep it short and move detail into `references/`, one level deep.
- The `description` frontmatter is the trigger: say what the skill does and when to use it, in at most 1024 characters.
- Never write a price into the skill. Prices are read from the environment per episode.
- Thresholds live in `data/`. Scripts read them and docs cite them.
- Scripts stay standard-library only, apart from the optional Pillow import. The person-aware effects (`person_*`, `fx_*`) are the exception: they need numpy, OpenCV and Pillow, import them
  at the top, and their tests skip when those are absent. Third-party files are downloaded on first use, pinned by sha256 in `data/assets.json`, never vendored; add new ones to `THIRD-PARTY.md`.
- Every invariant a script relies on gets a test.
- Never ship a price. Never weaken a spend guard to make a run easier: autonomy is a policy in `SKILL.md`, enforced by the ledger, not a bypass of it.
