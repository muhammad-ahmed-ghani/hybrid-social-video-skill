# Platforms: specs, safe zones, lengths, labels

As of 2026-10-20. Platform rules change quarterly and several pages could not be read
in full; re-open the primary page before a client delivery. Numbers live in
`data/platforms.json`, which `contact_sheet.py` and `qc_master.py` read. Each claim is
tagged: verified (read on a first-party page or measured from a first-party asset),
reported (a secondary source says so), or inference.

Platforms without an entry in `data/platforms.json` (the file covers TikTok, Instagram Reels and YouTube Shorts) raise lint E014:
the common safe box is used until the platform's own pages have been read for its zones, caption lanes and limits, and the
entry is added with its source.

## Contents
- [Delivery spec](#delivery-spec) · [Safe zones](#safe-zones) · [Captions](#captions)
- [Length](#length) · [Ranking signals](#ranking-signals) · [Labels and policy](#labels-and-policy)
- [Originality](#originality) · [Music](#music)

## Delivery spec

| Item | Value | Basis |
|---|---|---|
| Canvas | 1080x1920 (9:16). TikTok ads need at least 540x960; YouTube Shorts uploads max out at 1080p | verified |
| Frame rate | 24 to 60; deliver 30. YouTube encodes at the recorded rate | verified |
| Container and codec | MP4, H.264 High profile, progressive, 4:2:0, BT.709 SDR, moov atom first (`-movflags +faststart`) | verified (YouTube) |
| Video bitrate | YouTube SDR 1080p: 8 Mbps at 24 to 30 fps. TikTok in-feed minimum 516 kbps, file up to 500 MB | verified |
| Audio | AAC-LC, 48 kHz, stereo, 384 kbps | verified (YouTube) |
| Loudness | -14 LUFS integrated, true peak at or below -1 dBTP | inference: no platform publishes a target; EBU R128 (-23 LUFS) and Spotify (-14 LUFS, 1 dB headroom) are the only primary references |

`qc_master.py` gates integrated loudness at -17 to -11 LUFS and true peak at -0.3 dBTP,
and warns above -1 dBTP.

## Safe zones

Pixels at 1080x1920. These are UI-covered bands. They come from the platforms' own ad
safe-zone templates (organic overlays are at most as large; no organic template exists).

| Platform | Top | Bottom | Left | Right | Basis |
|---|---|---|---|---|---|
| TikTok in-feed | 240 | 660 | 120 | 120, plus a 180 px action rail (300 from the edge) for every row below y=840; mirrored to the left in the Arabic layout | verified (measured from the official PNG) |
| YouTube Shorts | 288 | 672 | 48 | 192 | verified (measured from the Google overlay PNG) |
| Instagram Reels | about 269 (14%) | about 672 (35%) | about 65 (6%) | about 65 | reported (Meta Ads Guide wording quoted by third parties) |

Combined box for all three, derived: top 288, bottom edge y 1248, left 120, right x 888.
Below y=840 the right limit is x 780. Practical lanes: full width x 120 to 888 for y 288 to
840; narrower x 120 to 780 for y 840 to 1248.

Other placement facts: the TikTok bottom margin grows with caption length (a one-line
caption leaves about 812 px in the older template, four lines about 1,014 px). Instagram's
profile grid crops to 3:4, which removes 240 px at top and bottom: keep the cover subject
in y 240 to 1680. Studio-style generic safe boxes (90% action-safe, 80% title-safe) are a
useful floor for composition work but are looser than these platform bands.

Never put captions at the common "lower third" below y 1250.

## Captions

- Phrase-level captions of 3 to 5 words, at most 2 lines, about 21 to 25 Latin
  characters per line at 60 px, on screen at least 0.8 s. No controlled evidence shows
  word-by-word highlighting raises retention; it is a styling choice.
- Caption lane A: y 620 to 840, full width, safe on all three platforms. Lane B: y 840
  to 1240 with x at most 780; mirror for TikTok's Arabic layout.
- Size: 56 to 72 px burned in; 40 px is the absolute floor. A 1080 px frame shows on a
  360 to 390 pt phone, so one point is about 2.8 to 3 frame pixels.
- Contrast at least 4.5:1 for normal text (3:1 for large). Over moving video there is no
  single background colour: use a box or a thick outline and test on the lightest and
  darkest frame.
- Majority-text reels and reels with borders are shown less on Instagram. Captions
  support the picture; they are not the whole frame.
- Emphasis: pair colour with weight or size. Colour alone fails colour-blind viewers.
- YouTube: also upload a sidecar SRT or VTT so captions can be toggled, searched and
  translated. Burned-in captions alone are not accessible to screen readers.
- RTL (Arabic, Urdu): see `12-localization.md`.
- TikTok's own advice of "5 to 10 words per second" of text exceeds silent reading
  speed (about 238 wpm for English adults). Ignore it as a caption rule.

## Length

Platform-side: any vertical or square video up to 3 minutes uploaded after
2024-10-15 is a Short (verified). Reels may be up to 3 minutes and Reels over 3
minutes are not placed in the Reels tab (reported). TikTok ad specs allow up to 10
minutes; the organic limit was not verified.

Observed, confounded data: Instagram Reels (9.77M reels, 1H 2026) median views peaked at
45 to 60 s and were lowest under 30 s; TikTok business views rose with length. Neither
says shorter is better. One-account data went the other way. Defaults: 30 to 60 s for a
one-concept explainer; 60 to 90 s with 2 to 3 distinct beats plus a loop device; do not
exceed 3 minutes on Instagram. On YouTube a Short over 1 minute with licensed music
risks a Content ID block.

## Ranking signals

What each platform states, no weights published:

| Signal | TikTok | Instagram Reels | YouTube Shorts |
|---|---|---|---|
| finish and watch time | finishing a longer video weighs more than a weak indicator | predicts "watch all the way through"; watch time is a named top signal | "engaged views", satisfaction surveys |
| rewatch | replays seed early recommendations | a good transition makes people watch again | replays count as views since 2025-03-31, all formats from 2026-08-24 |
| shares and sends | shares are an interaction | predicts reshare; sends per reach reported as a top signal | not named |
| originality | unoriginal or reused material is ineligible for the For You feed | aggregators lose recommendations; watermarks and added subtitles do not make a repost original | inauthentic content is not monetisable |

Design for one deliberate replay hook (a transition or reveal) and a share-oriented close
("send this to someone who...") over follow bait. A genuine, specific question tied to the
content is fine; "comment X to get Y" mechanics sit inside TikTok's manipulation wording.

Old and new YouTube Shorts view counts are not comparable: compare on engaged views or
percent viewed.

## Labels and policy

| Platform | Rule | Basis |
|---|---|---|
| TikTok | label AI-generated or significantly edited content showing realistic scenes or people; unlabelled content may be removed, restricted or labelled. Guidelines effective 2026-09-24. Reads C2PA, applies invisible watermarks on its own tools | verified |
| YouTube disclosure | disclose realistic synthetic content: a real person saying or doing something they did not, altered footage of a real event or place, a realistic scene that never occurred. Not needed for clearly unrealistic or animated content, scripts, captions, upscaling, voice repair, cloning your own voice. C2PA content is labelled automatically and the creator cannot remove that label | verified |
| YouTube monetisation | "inauthentic content" (renamed 2025-07-15): generic or unoriginal templates, mass-produced content, slideshows with minimal narrative, stitched unrelated AI clips are ineligible. An AI persona posing as a human expert on health, legal, finance or politics is ineligible | verified |
| Instagram and Meta | AI info labels from detected indicators or self-disclosure; from 2026-08-31 a profile featuring an AI-generated person needs the AI-generated profile label or its reach is limited | verified (fetched summary) |
| EU AI Act Article 50 | applies from 2026-08-02: deployers disclose deepfakes (AI content resembling existing persons, places or events that would falsely appear authentic); providers machine-mark outputs. Code of practice final 2026-06-10 | verified |
| India, China | synthetic-content labelling rules in force since 2026-02-20 and 2025 respectively | reported |

Operating rules: realism is the trigger. A stylised illustration or code graphic needs no
label on YouTube and does not meet the EU deepfake definition. Photoreal AI of a real
place or event does, so do not make it. If realistic synthetic content remains, turn on
the platform flag and add an on-screen label. If a reel might be boosted as an ad,
labels may also be required in the EU, India and New York. This is a design rule, not
legal advice.

## Originality

Instagram's originality system and TikTok's For You eligibility reward added
information. Do not burn a platform watermark or a competitor's logo into the picture. A
reel built from someone else's clip with only subtitles added counts as unoriginal. Add
new information, context or a point of view, and keep it your own work.

## Music

On YouTube each music track in a Short diverts revenue to music partners (one track,
half), royalty-free Audio Library tracks avoid Content ID claims, and Shorts over 1
minute with an active claim are blocked. Prefer cleared or generated music and keep to
one track. Trending audio has no measured lift for an explainer whose value is the
narration.
