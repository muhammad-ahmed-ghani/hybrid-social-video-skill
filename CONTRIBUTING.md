# Contributing

1. Branch off `main`: `fix/short-slug` for repairs, `feature/short-slug` for additions.
2. Edit the skill under `skills/hybrid-social-video/`.
3. Run the tests: `python3 -m pytest -q skills/hybrid-social-video/tests/`.
4. Rebuild the archive: `python3 tools/package_skill.py`, and commit `dist/hybrid-social-video.skill` with your change.
5. Add a line to `CHANGELOG.md`. Bump `metadata.version` in `SKILL.md` for user-visible changes.

## Skill rules

- `SKILL.md` addresses the agent. Keep it short and move detail into `references/`, one level deep.
- The `description` frontmatter is the trigger: say what the skill does and when to use it, in at most 1024 characters.
- Never write a price into the skill. Prices are read from the environment per episode.
- Thresholds live in `data/`. Scripts read them and docs cite them.
- Scripts stay standard-library only, apart from the optional Pillow import.
- Every invariant a script relies on gets a test.
