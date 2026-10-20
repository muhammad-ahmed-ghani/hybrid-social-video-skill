#!/usr/bin/env python3
"""reference_scan.py - look at how people make public reels on a topic, to choose a hook, length and pace with evidence.

    python3 reference_scan.py find      --topic "compound interest" [--n 8] [--max-seconds 90] [--any-shape] [--budget 75] --out episode/references.json
    python3 reference_scan.py add       --urls urls.txt --out episode/references.json     # urls from your own web search (any platform)
    python3 reference_scan.py analyze   --refs episode/references.json [--limit 8] [--no-download] [--keep-channel]
    python3 reference_scan.py summarize --refs episode/references.json [--json]

What it is for: craft, not facts. From 5 to 10 public reels on the user's topic it reads the hook type and wording, length, number
of cuts and average shot length, loudness, and which hooks and formats are overused, then writes a short note the agent uses
when it picks the format, the hook and the pace, and when it decides how to be different. Facts still need sources
(`claims[]`); trending is not the same as good.

How: `find` searches YouTube (Shorts and short videos) through yt-dlp's search, metadata only, keeping vertical videos (use --any-shape to keep all). TikTok and Instagram have no open
search, so the agent collects their public URLs with its own web search and passes them with `add`. `analyze` downloads each
video at low resolution into a temporary folder, measures it, and deletes the file; `--no-download` keeps to metadata. The hook is
the first six seconds transcribed locally (faster-whisper) when available, else the title.

Rules (also in references/18-reference-scan.md): public pages only; stop at a login, captcha or age wall and mark the item
`blocked`, never bypass it; no personal data is stored (the channel name is dropped unless `--keep-channel`); downloads are
deleted; nothing is redistributed; the output is technique (hook type, pace, length), never content to copy; a request the platform
refuses is not retried in a loop. Network access and yt-dlp are needed for `find`/`analyze`; without them the scan is skipped and
the skip is written into `meta.notes`, never a question.

`find` makes one attempt per page inside a time budget (--budget seconds, default 75) and stops at the first sign of a wall
(three unreadable pages and nothing read): it prints the count of unreadable pages and exits 3, so an agent can tell a wall from
a bug and move on in under two minutes.

Exit 0 ok | 2 usage | 3 yt-dlp or network missing, or nothing readable (a wall).
"""
from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hx_common import eprint, parse_args  # noqa: E402

NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "first", "top", "best"}


def platform_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    for key, name in (("youtube", "youtube"), ("youtu.be", "youtube"), ("tiktok", "tiktok"), ("instagram", "instagram")):
        if key in host:
            return name
    return "other"


def classify_hook(text: str) -> str:
    """A rough label for how a reel opens: question, number, warning, claim, story or statement."""
    t = (text or "").strip().lower()
    if not t:
        return "unknown"
    first = " ".join(re.findall(r"[a-z0-9'?]+", t)[:8])
    if "?" in t[:80] or re.match(r"^(how|why|what|did|do|does|can|is|are|have|ever|who|when|where)\b", first):
        return "question"
    if re.match(r"^(stop|never|don't|dont|do not|avoid|quit|please)\b", first):
        return "warning"
    if re.search(r"\b\d+\b", first) or any(w in NUMBER_WORDS for w in first.split()[:4]):
        return "number"
    if re.match(r"^(i |i'm|i've|my |when i|last (year|week|month)|so i|yesterday)", first):
        return "story"
    if re.search(r"\b(nobody|everyone|wrong|myth|secret|actually|truth|lie|never tell|they don't)\b", first):
        return "claim"
    return "statement"


def _ytdlp() -> str | None:
    return shutil.which("yt-dlp")


def _run_json(cmd: list[str], timeout: int = 90) -> list[dict]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception:
        return []
    out = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


def _item(url: str, meta: dict | None = None, keep_channel: bool = False) -> dict:
    meta = meta or {}
    it = {"platform": platform_of(url), "url": url, "id": meta.get("id"), "title": meta.get("title"),
          "duration_s": meta.get("duration"), "views": meta.get("view_count"), "likes": meta.get("like_count"),
          "comments": meta.get("comment_count"), "upload_date": meta.get("upload_date"),
          "width": meta.get("width"), "height": meta.get("height"), "status": "ok"}
    if meta.get("width") and meta.get("height"):
        it["vertical"] = meta["height"] > meta["width"]
    if keep_channel:
        it["channel"] = meta.get("uploader") or meta.get("channel")
    return it


def _load(path: str) -> dict:
    p = Path(path)
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"schema": "hybrid-references/1", "topic": None, "generated": None, "items": []}


def _save(path: str, doc: dict) -> None:
    doc["generated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False))


STOP = {"the", "and", "for", "with", "how", "what", "why", "does", "this", "that", "from", "your", "explained", "about", "into", "work", "works"}


def topic_tags(topic: str) -> list[str]:
    """Hashtags to look under: the whole topic as one tag, then its longer words."""
    words = [w for w in re.findall(r"[a-z0-9]+", topic.lower()) if len(w) >= 4 and w not in STOP]
    tags = ["".join(re.findall(r"[a-z0-9]+", topic.lower()))] + words
    seen, out = set(), []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:4]


def cmd_find(opt: dict) -> int:
    topic = str(opt.get("topic", "")).strip()
    if not topic or not opt.get("out"):
        eprint("--topic and --out are required")
        return 2
    if not _ytdlp():
        eprint("yt-dlp is not installed: skipping the YouTube search. Collect public reel URLs with a web search and pass them to `add`.")
        return 3
    n, max_s = int(opt.get("n", 8)), float(opt.get("max-seconds", 90))
    doc = _load(opt["out"])
    doc["topic"] = topic
    have = {i["url"] for i in doc["items"]}
    cands: list[str] = []
    if not opt.get("any-shape"):
        for tag in topic_tags(topic):                      # the Shorts tab of a hashtag lists real vertical Shorts
            rows = _run_json(["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings", "--playlist-end", str(n * 2),
                              f"https://www.youtube.com/hashtag/{tag}/shorts"], timeout=60)
            cands += [r.get("url") or r.get("webpage_url") for r in rows if r.get("url") or r.get("webpage_url")]
            if len(set(cands)) >= n * 2:
                break
    if not cands:                                          # fallback: ordinary search, any shape
        rows = _run_json(["yt-dlp", "--flat-playlist", "--dump-json", "--no-warnings", f"ytsearch{n * 3}:{topic} shorts"])
        cands = [r.get("url") or r.get("webpage_url") for r in rows if r.get("url") or r.get("webpage_url")]
    if not cands:
        eprint("the search returned nothing (offline, rate limited or blocked): skipping, not retrying in a loop")
        return 3
    added = 0
    failed = 0
    tried: list[str] = []
    t_start = time.time()
    budget = float(opt.get("budget", 75))                    # one attempt, a time budget, then stop: never a retry loop
    for url in dict.fromkeys(cands):
        if url in have:
            continue
        if time.time() - t_start > budget:
            eprint(f"[scan] time budget of {budget:g} s used: stopping with what was read")
            break
        got = _run_json(["yt-dlp", "--dump-json", "--skip-download", "--no-warnings", url], timeout=45)
        meta = got[0] if got else {}
        tried.append(url)
        if not meta:
            failed += 1
            if failed >= 3 and added == 0:                    # three refusals in a row and nothing read: a wall, not bad luck
                break
            continue
        d = meta.get("duration")
        if d and d > max_s:
            continue
        doc["items"].append(_item(url, meta, bool(opt.get("keep-channel"))))
        have.add(url)
        added += 1
        if added >= n:
            break
    if added == 0 and failed:
        doc["skipped_reason"] = (f"{failed} public page(s) could not be read (a bot or sign-in wall, a rate limit or no network); "
                                 f"tried: {', '.join(tried[:3])}")
    _save(opt["out"], doc)
    print(json.dumps({"added": added, "items": len(doc["items"]), "unreadable": failed, "out": opt["out"],
                      "skipped_reason": doc.get("skipped_reason")}))
    if added == 0 and failed:
        eprint(f"[scan] {failed} page(s) could not be read (a bot or sign-in wall, rate limit or no network): the scan is skipped, never bypassed. "
               "Write the skip into meta.notes and carry on.")
        return 3
    return 0


def cmd_add(opt: dict) -> int:
    if not (opt.get("urls") and opt.get("out")):
        eprint("--urls FILE and --out are required")
        return 2
    urls = [u.strip() for u in Path(opt["urls"]).read_text().splitlines() if u.strip().startswith("http")]
    doc = _load(opt["out"])
    have = {i["url"] for i in doc["items"]}
    added = 0
    for u in urls:
        if u in have:
            continue
        meta = {}
        if _ytdlp():
            got = _run_json(["yt-dlp", "--dump-json", "--skip-download", "--no-warnings", u], timeout=60)
            meta = got[0] if got else {}
        it = _item(u, meta, bool(opt.get("keep-channel")))
        if not meta:
            it["status"] = "blocked" if _ytdlp() else "unread"
            it["note"] = "metadata not readable without logging in (or yt-dlp missing); not bypassed"
        doc["items"].append(it)
        added += 1
    _save(opt["out"], doc)
    print(json.dumps({"added": added, "items": len(doc["items"]), "out": opt["out"]}))
    return 0


def _probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
        st = j["streams"][0]
        return {"width": st["width"], "height": st["height"], "duration": float(j["format"]["duration"])}
    except Exception:
        return {}


def _cuts(path: Path) -> int:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf", "scale=160:-2,select='gt(scene,0.30)',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return len(re.findall(r"pts_time:", r.stderr))


def _lufs(path: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    tail = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    return float(m.group(1)) if m else None


def _hook_text(path: Path) -> str | None:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    try:
        model = WhisperModel("base.en", device="cpu", compute_type="int8")
        segs, _ = model.transcribe(str(path), language="en", vad_filter=False)
        out = []
        for s in segs:
            if s.start > 6.0:
                break
            out.append(s.text.strip())
        return " ".join(out).strip() or None
    except Exception:
        return None


def measure(path: Path) -> dict:
    """Measure one local video file: size, length, cuts, average shot, loudness, hook text and type."""
    pr = _probe(path)
    if not pr:
        return {}
    cuts = _cuts(path)
    dur = pr["duration"]
    res = {"width": pr["width"], "height": pr["height"], "vertical": pr["height"] > pr["width"], "duration_s": round(dur, 2),
           "cuts": cuts, "avg_shot_s": round(dur / (cuts + 1), 2), "lufs": _lufs(path)}
    text = _hook_text(path)
    if text:
        res["hook_text"], res["hook_source"] = text, "speech"
    return res


def cmd_analyze(opt: dict) -> int:
    if not opt.get("refs"):
        eprint("--refs FILE is required")
        return 2
    doc = _load(opt["refs"])
    limit = int(opt.get("limit", 10))
    todo = [i for i in doc["items"] if i.get("status") == "ok"][:limit]
    if opt.get("no-download"):
        for it in todo:
            if it.get("title") and not it.get("hook_text"):
                it["hook_text"], it["hook_source"] = it["title"], "title"
    else:
        if not _ytdlp():
            eprint("yt-dlp is not installed: analysing from metadata only")
            return 3
        for it in todo:
            with tempfile.TemporaryDirectory() as td:
                r = subprocess.run(["yt-dlp", "-f", "bv*[height<=480]+ba/b[height<=480]/worst", "--max-filesize", "40M", "--no-playlist",
                                    "--no-warnings", "-o", f"{td}/v.%(ext)s", it["url"]], capture_output=True, text=True, timeout=180)
                files = [f for f in Path(td).glob("v.*") if f.suffix not in (".part", ".ytdl")]
                if r.returncode != 0 or not files:
                    it["status"] = "blocked"
                    it["note"] = "not fetched (a login or age wall, the size limit, or an error): skipped, never bypassed"
                    continue
                it.update(measure(files[0]))
            # the temp folder, and the video in it, is gone here
            if not it.get("hook_text") and it.get("title"):
                it["hook_text"], it["hook_source"] = it["title"], "title"
    keys = [w for w in re.findall(r"[a-z0-9]+", str(doc.get("topic") or "").lower()) if len(w) >= 4 and w not in STOP]
    for it in doc["items"]:
        if it.get("hook_text"):
            it["hook_type"] = classify_hook(it["hook_text"])
            it["hook_words"] = len(it["hook_text"].split())
        if keys:
            blob = f"{it.get('title') or ''} {it.get('hook_text') or ''}".lower()
            it["on_topic"] = any(k in blob for k in keys)
    _save(opt["refs"], doc)
    ok = sum(1 for i in todo if i.get("status") == "ok")
    print(json.dumps({"analysed": ok, "blocked": sum(1 for i in todo if i.get("status") == "blocked"), "refs": opt["refs"]}))
    return 0


def summarize(doc: dict) -> dict:
    readable = [i for i in doc.get("items", []) if i.get("status") == "ok"]
    on = [i for i in readable if i.get("on_topic", True)]
    items = on if len(on) >= 4 else readable                 # hashtags are loose: drop off-topic reels when enough remain
    dropped = len(readable) - len(items)
    n = len(items)
    plat: dict[str, int] = {}
    for i in items:
        plat[i["platform"]] = plat.get(i["platform"], 0) + 1
    med = lambda k: round(statistics.median([i[k] for i in items if i.get(k) is not None]), 2) if any(i.get(k) is not None for i in items) else None
    hooks: dict[str, int] = {}
    for i in items:
        if i.get("hook_type"):
            hooks[i["hook_type"]] = hooks.get(i["hook_type"], 0) + 1
    dur = [i["duration_s"] for i in items if i.get("duration_s")]
    s = {"scanned": n, "platforms": plat, "median_duration_s": med("duration_s"), "duration_range_s": [min(dur), max(dur)] if dur else None,
         "median_avg_shot_s": med("avg_shot_s"), "median_hook_words": med("hook_words"), "hook_types": hooks,
         "share_vertical": round(sum(1 for i in items if i.get("vertical")) / n, 2) if n else None}
    notes: list[str] = []
    if dropped:
        notes.append(f"{dropped} reel(s) were off-topic (hashtags are loose) and are left out")
    if n < 5:
        notes.append(f"only {n} readable reel(s): treat this as a hint, not a pattern")
    if hooks:
        top, cnt = max(hooks.items(), key=lambda kv: kv[1])
        if cnt / sum(hooks.values()) >= 0.6 and sum(hooks.values()) >= 4:
            notes.append(f"{cnt} of {sum(hooks.values())} open with a {top} hook: it is the overused opener here, so open differently (and still inside 3 s)")
        else:
            notes.append("hook types are mixed: no single opener dominates")
    if s["median_avg_shot_s"] is not None:
        notes.append(f"typical pace is a visual change every {s['median_avg_shot_s']} s: plan the beat band and overlay changes at or under that")
    if s["median_duration_s"]:
        notes.append(f"typical length is {s['median_duration_s']} s: a target near it is safe; going well over needs a reason")
    notes.append("use this for craft only: take the technique, never the content, and keep every fact behind a claim")
    s["notes"] = notes
    return s


def cmd_summarize(opt: dict) -> int:
    if not opt.get("refs"):
        eprint("--refs FILE is required")
        return 2
    doc = _load(opt["refs"])
    s = summarize(doc)
    doc["summary"] = s
    _save(opt["refs"], doc)
    if opt.get("json"):
        print(json.dumps(s, indent=2))
    else:
        print(f"Scanned {s['scanned']} public reel(s) {s['platforms']}.")
        for line in s["notes"]:
            print(f"- {line}")
    return 0


def main(argv: list[str]) -> int:
    pos, opt = parse_args(argv, flags={"no-download", "keep-channel", "any-shape", "help", "h", "json"})
    if opt.get("help") or opt.get("h") or not pos:
        print(__doc__)
        return 0 if opt.get("help") or opt.get("h") else 2
    fn = {"find": cmd_find, "add": cmd_add, "analyze": cmd_analyze, "summarize": cmd_summarize}.get(pos[0])
    if not fn:
        eprint(f"unknown command '{pos[0]}'")
        return 2
    return fn(opt)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
