# Reference scan: how are people making this?

Before choosing the format, the hook and the pace for a topic-based video, look at 5 to 10 public reels on the same topic. This is
research for craft: the opener people use, how long the videos run, how often the picture changes, how loud they are, and which
treatments are overused. It does not make facts more accurate (facts need sources and a `claims[]` entry) and it is not a template
to copy: the point is to know what the feed already looks like so that yours is better and different.

## Contents
- [When it runs](#when-it-runs) · [How](#how) · [What to take from it](#what-to-take-from-it)
- [Limits and rules](#limits-and-rules) · [Record it](#record-it)

## When it runs

Automatically, with no question, at step G0 of the loop for any video built from a topic, article, paper or show idea, when the
network and `yt-dlp` are available. Skip it silently, and write the skip into `meta.notes`, when:
- the user supplied a finished script, a reference video "like this" (analyse that one instead), or footage to recut;
- there is no network or no `yt-dlp`, or the platform returns nothing (do not retry in a loop);
- the topic is private or personal (nothing public to look at).

## How

```bash
python3 scripts/reference_scan.py find --topic "<topic>" --n 8 --out episode/references.json     # YouTube Shorts, metadata
python3 scripts/reference_scan.py add  --urls urls.txt --out episode/references.json              # TikTok / Instagram / any public URLs
python3 scripts/reference_scan.py analyze   --refs episode/references.json --limit 8              # low-res download, measure, delete
python3 scripts/reference_scan.py summarize --refs episode/references.json                         # the note
```

- **YouTube.** `find` reads the Shorts tab of the topic's hashtags (a plain search mostly returns horizontal videos), then the full
  public metadata of each, and keeps vertical videos under the length limit.
- **TikTok and Instagram.** Neither has an open search. Use your own web search tool for public reel pages on the topic and pass
  the URLs to `add` (one per line in `urls.txt`). Their pages often need a login for the video itself: the item is marked `blocked`
  and skipped. Never bypass a wall.
- **Measure.** `analyze` downloads each video at 480p or less into a temporary folder, reads the size, length, number of cuts,
  average shot length and loudness, transcribes the first six seconds locally for the hook (the title when there is no recogniser),
  classifies the hook (question, number, warning, claim, story, statement) and deletes the file. `--no-download` keeps to metadata.
- **Summarise.** `summarize` writes the aggregate into `references.json` and prints a few lines: typical length, typical shot length,
  which hook dominates, and what is overused. Hashtags are loose: off-topic reels are left out when enough on-topic ones remain.

## What to take from it

Use it to decide, then record what you decided and why in `meta.notes`:
- **Hook.** If one opener dominates (most open with a question, say), open differently, and still inside 3 seconds. If they are
  mixed, choose by the story intent as usual.
- **Length and pace.** Target near the typical length; set the beat band and the rate of overlay changes at or under the typical
  shot length. A video far slower than the feed needs a reason (a host with charisma, a deliberate hold).
- **Format.** If every reel in the set is a talking head, a code-drawn explainer stands out; if every one is a collage, a host does.
  Do not pick a format only because the feed uses it.
- **Be different on purpose.** Name one thing you will do that the sample does not. That is the opposite of a template.

## Limits and rules

- Public pages only. Stop at a login, captcha or age wall and mark the item `blocked`. Never log in, solve a captcha, rotate
  identities or otherwise get around a wall, and do not retry a refusal in a loop.
- No personal data. The channel name is dropped unless `--keep-channel`; no comments, faces or handles are stored.
- Downloads are temporary and deleted. Nothing from the sample is redistributed or reused in the video.
- Technique, not content: take the hook type, length and pace, never the words, footage, music or a creator's identity
  (`SKILL.md`, pitfalls). Facts still come from sources.
- Platforms' terms apply. Metadata through a platform's own public pages and a low-resolution local analysis for research is the
  scope here; if the platform objects, stop. The scan is optional and the video does not depend on it.
- A handful of reels is a hint, not a pattern: with fewer than 5 readable ones the note says so.

## Record it

Add one entry to `provenance.json` so the delivery note can say it happened:

```bash
python3 scripts/provenance.py add --episode episode --role reference --ai false --tool "reference_scan.py (yt-dlp, faster-whisper)" \
    --used-for "8 public reels analysed for hook, length and pace; none copied" --data-sent "topic keywords to the platform"
```
