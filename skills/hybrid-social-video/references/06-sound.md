# Sound: voice, music, effects, loudness

Sound is half the video and the cheapest place to look amateur. Levels, placement and
sync below are measured where marked. Evidence tags: V verified (primary source or local
test), R reported, I inference. Mixing mechanics (ducking, buses, automation) belong to
`/hyperframes-audio`; sourcing and voice generation to `/media-use`.

## Contents
- [One decision first](#one-decision-first) · [Voice direction](#voice-direction)
- [Loudness](#loudness) · [Levels and ducking](#levels-and-ducking) · [Sound effects](#sound-effects)
- [Silence, hook and stems](#silence-hook-and-stems) · [Sync](#sync) · [Density](#density) · [Quick checks](#quick-checks)

## One decision first

Some projects forbid processing audio that a generated video clip carries (no loudnorm,
fades or re-encode of segment audio; concat only), because it risks lip-sync and timbre.
Everything about loudness and ducking below applies to the final mix of audio YOU build:
voice-over, music, effects, ambience as separate stems. For any clip with model-generated
audio, decide per episode and write it into `beatmap.json`:

- keep the clip's audio untouched and concat (used when it is the host's own voice, the
  master clock), or
- discard it and replace the track with your own stems (used for b-roll, where the
  voice-over owns the mix).

Never normalise one segment and not its neighbour. Never mux a separate voice onto an
avatar clip (`11-routing.md`).

## Voice direction

- One continuous voice-over per reel so prosody does not reset at beat boundaries; one voice
  across a language switch. In a story, each character has one continuous performance per scene
  in its own stored voice, and a character's voice is never swapped. Default pace 1.0; a 1.1
  speed-up read as too fast for a host avatar. Set pace as a parameter of the voice engine before
  synthesis and re-synthesise to change it. Never apply a tempo change after synthesis: that is
  the retiming the iron rules forbid, and anything lip-syncing to the audio follows the audio as it
  is.
- Performance markup lives only in `tts_text`: capitalise the 1 to 3 emphasis words, end a
  suspense line with an ellipsis, use a dash for a hard turn, and at most one engine audio tag
  at the front of a line from a whitelist. About one tag per two beats; the hook and the
  payoff get the strongest; never tag a chart-only beat. An unknown tag can be spoken aloud.
  Captions read `text`, never `tts_text`. Keep expressive stability in the natural range:
  pushing stability to its maximum setting suppresses tags.
- Numbers, dates and units in `tts_text` are written as spoken; some engines misread
  "$1,000,000", "01/02/2023" and units. Keep a pronunciation list for names.
- Flat audio produces a static avatar and a flat explainer: give emotional range to the hook
  and the reveal.
- Synthetic voice policy and language support: `07-ai-layer.md` and `12-localization.md`.
  Choose a human-sounding voice and audition 3 candidates on the real script; the voice
  principle in multimedia learning favours appealing human or high-quality TTS voices over
  flat machine delivery.

## The voice ladder

Best first, and the skill picks without asking the user:

1. The user's own recording, or a real presenter.
2. Host-native speech: a video model that speaks the line while the host moves (`17-ai-models-and-tools.md`). Its audio is the master clock.
3. A neural or human-grade text-to-speech tool (read its voice list; send the whole script in one call).
4. A system voice (macOS `say`, espeak, a small local model): **draft only**. It is acceptable for an animatic and as the last
   resort when nothing better is reachable; then the final note says it is a draft and names the upgrade.

Audition by measurement, not by asking: render the same two or three lines on each reachable route and run
`scripts/voice_check.py` (round-trip word error, pace, level). Drop what fails, keep the best that is not `draft`. If the
user later says a voice is robotic or wrong, that is a defect: move up the ladder and re-run assembly (it is free); only the
voice itself is paid.

## Loudness

No platform publishes a loudness target for TikTok, Instagram or Shorts. Documented
references: EBU R128 is -23.0 LUFS with a true peak ceiling of -1 dBTP (broadcast); Spotify
normalises to -14 LUFS and asks for true peak below -1 dBTP (below -2 dBTP if louder than
-14). YouTube reportedly turns loud audio down and does not raise quiet audio (R).

Delivery target (I): final mix -14 LUFS integrated (plus or minus 0.5), true peak at most
-1.0 dBTP (-1.5 when headroom matters for AAC transcodes), loudness range about 5 to 9 LU,
48 kHz. Quieter than about -16 sounds weak where nothing raises it. `qc_master.py` gates
-17 to -11 LUFS and -0.3 dBTP and warns above -1 dBTP.

Two-pass recipe, measured to land on target (single-pass was 0.5 LU off). ffmpeg's loudnorm
defaults are I=-24, LRA=7, TP=-2, so pass every value explicitly:

```bash
# pass 1: measure
ffmpeg -i mix.wav -af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -
# pass 2: apply with the measured values (input_i, input_tp, input_lra, input_thresh, target_offset)
ffmpeg -i mix.wav -af "loudnorm=I=-14:TP=-1:LRA=11:measured_I=<..>:measured_TP=<..>:measured_LRA=<..>:measured_thresh=<..>:offset=<..>:linear=true" mix_14.wav
# always re-measure the file you will upload
ffmpeg -i final.mp4 -af ebur128=peak=true -vn -f null -
```

## Levels and ducking

Measure the music-to-voice ratio inside voice-over windows with the same method for both
(short-term loudness or RMS). Published rules differ because they measure different things:
"how far below the voice the music sits during speech" (about 18 to 25 dB) versus "how far the
music is pulled down from its un-ducked level" (about 6 to 12 dB). A bed mixed 8 to 10 dB under
the voice in open passages and ducked another 6 to 12 dB under speech lands near 14 to 22 dB
below speech, which fits all of them.

| Content | Music to voice inside VO windows |
|---|---|
| narrated explainer, music as texture | 14 to 20 dB below |
| energetic montage, short simple lines | 10 to 14 dB |
| dense information, accessibility, noisy listening | 20 dB or more (WCAG 1.4.7 AAA asks at least 20 dB) |
| under 10 dB | masks speech |
| music-only gaps of 2 s or more | allow a +6 to +10 dB swell, then duck again |
| SFX bed | about 6 to 12 dB below voice RMS; hits may briefly reach voice peak |

K-weighting under-weights bass, so a bass-heavy bed can mask speech while measuring far below
it. Always listen on a phone speaker and in earbuds.

Ducking, preferred method when the voice timing is known (it always is, from TTS alignment):
automate music gain from the word timestamps. Down-ramp 40 to 80 ms starting 100 to 200 ms
before the first word (a sidechain cannot look ahead), hold while speech continues, bridge gaps
shorter than 0.4 to 0.6 s so the bed does not pump between words, up-ramp 400 to 700 ms after the
last word. Exact, repeatable, seek-safe.

Sidechain method, when timing is unknown. ffmpeg `sidechaincompress` threshold is a LINEAR amplitude
(0.02 is -34 dBFS). Measured duck depths on a synthetic voice at -20 dBFS RMS with attack 20 ms and
release 400 ms: threshold 0.05 ratio 4 gave -8 dB; 0.02 ratio 4 gave -14 dB; 0.02 ratio 8 gave -16.5
dB; 0.01 ratio 4 gave -18.6 dB. The detector reacts to peaks, not averages, so calibrate by
measuring on the real voice-over: render, measure music-only level in voice windows versus idle
windows, adjust the threshold until the ratio hits the table. Published starting points: attack
30 to 80 ms, release 250 to 700 ms (lengthen if it pumps), ratio 3:1 to 6:1.

## Sound effects

| Effect | Use | Lands | Length and level | Notes |
|---|---|---|---|---|
| whoosh | whips, big slides, zoom-throughs | swell starts 100 to 300 ms early; the transient lands within about 1 frame of the visual landing or cut | 0.2 to 0.5 s; 6 to 12 dB under voice | direction matches motion; one per transition, never per element |
| riser | into a reveal or chapter change | 1 to 4 s ending exactly on the reveal frame, then a hit or a deliberate cut to silence | stays under voice until the last 0.5 s | 1 or 2 per video or they stop signalling |
| hit or impact | title slam, big number landing | on the landing frame or 1 frame late, never 2 or more early | 0.3 to 1.2 s; may reach voice peak | duck music 3 to 6 dB for its length |
| tick or click | counters, marks appearing | on the visual event frame | 30 to 100 ms | count-ups: a rising pitch or one end tick, not a tick per integer |
| pop | word pops, stickers | word-onset frame | 40 to 120 ms | vary pitch plus or minus 2 semitones; never identical back to back |
| paper slap, rustle, tear | collage looks | slap on the land frame; rustle 2 to 4 frames before | 0.1 to 0.4 s | pair with 8 to 12 fps stepped motion |
| keyboard or typewriter | terminal looks, search bars | one click per character only at about 15 characters per second or slower | 20 to 50 ms | keep it quiet |
| sting | brand bug, end card | on the logo landing | 0.5 to 1.5 s | part of the brand kit |

Same effect family per identity: paper for collage, clicks for terminal, pops for creator.

## Silence, hook and stems

- Silence is a tool: a 0.3 to 0.6 s musical dropout just before a reveal, or a 0.4 to 0.8 s
  voice pause after a surprising number. Never leave digital silence: keep a low bed (music or
  room tone about -45 to -35 dBFS) under cuts and gaps so edits do not click. `silencedetect`
  at -50 dB flags true digital silence. For hosted segments, lay 10 s or more of the real room
  tone under any cutaway.
- Sound exists at frame 0: no fade-in from silence, no long music intro. Start the first word
  within 0.1 to 0.3 s, or a percussive sting or riser that peaks on the hook line. A riser into
  the hook only works if it is audible from the first frame; never delay the first visual for
  audio. Frame 0 shows the tension while the voice starts mid-claim. Always add captions too:
  many viewers start muted, yet Instagram demotes muted reels. One platform study found 73% of
  its users stop and look at ads that use sound.
- Keep stems: `vo.wav`, `music.wav`, `sfx.wav`, `ambience.wav` at 48 kHz, 24-bit or float, plus
  the mastered mix (AAC-LC, 48 kHz, stereo, at least 192 kbps) and a cue sheet of timestamps and
  effect ids. Stems let you re-duck and re-normalise without a re-render.
- One music track only (YouTube Shorts revenue and claim rules, `10-platforms.md`); generated
  or cleared music; instrumentals; no artist names in prompts (`07-ai-layer.md`).

## Sync

Frame arithmetic: one frame is 41.7 ms at 24 fps, 33.3 ms at 30, 16.7 ms at 60. A broadcast
standard puts detectability at about +45 ms (audio early) to -125 ms (audio late), and
acceptability at +90 to -185 ms (R, derived from newsreader clips). So audio 2 frames early at
30 fps (67 ms) is detectable; audio up to about 3 frames late is not. Place effect transients on
the frame or 0 to 2 frames late, never more than 1 frame early. Word pops: ASR or alignment word
onset minus at most 1 frame.

Calibration check (measured to work): render a cue with a white flash and a 1 kHz click at a known
time, measure the first bright frame (`signalstats`, YAVG above 128) and the first audio onset,
and fail if the delta exceeds about 17 to 33 ms. In the test both landed at 2.000 s and `ffprobe`
showed `start_time` 0 for both streams.

## Density

Murch's rule: layers from the same part of the spectrum balance at about two and a half;
spread from speech to music the ceiling is about five; at six, clarity is lost. Voice plus music
plus sparse effects plus ambience is within the limit; two simultaneous effects of the same type plus
music already crowd. Vary density with the drama: denser at rehooks, thinner at the payoff.

Effect rules: effects only for the hero motion of a beat, secondary motion silent; on average at most
1 effect per 1.5 to 2 s; no two transients within 120 ms unless designed as one hit; never an effect
on every cut (1 cut in 3 or 4 is an event); an effect must not mask the first or last 100 ms of a
spoken word.

## Quick checks

Integrated -14 plus or minus 0.5 LUFS; true peak at most -1.0 dBTP; no digital silence over 0.3 s
except designed dropouts; music-to-voice ratio per the table; no effects within 100 ms of each other
unless designed; calibration cue within 1 frame; first audio within 0.3 s of frame 0; stems archived.
`qc_master.py` covers loudness, true peak and first-audible time; the rest are listening and
measurement steps in `09-qa.md`.
