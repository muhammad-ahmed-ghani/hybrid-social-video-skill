# Map and evidence (`map-evidence`)

Family editorial · tier R1 · 30 to 90 s · 2.5 words/s · gates G1 (G2 only if illustrated assets define the look) ·
cost scout-priced (drivers: illustrated assets, if any) · build time 25 to 60 min

Geography and documents carry the argument. A map moves to the place, a headline or a filing appears with the key
line highlighted, a number counts up, a quote lands with its source. This is the register of geopolitics, trade and
economics explainers: the viewer is shown where and what the evidence says, not told. The exactness comes from code
(real geodata, real captured documents), so invention has no room.

## Use when, avoid when

Use when place or paper is the story: why a strait, border, route, pipeline or city matters; what a law, filing, treaty or
article actually says; how events line up on a map and a calendar. Intents: causal, news, timeline, case, policy,
numbers (spatial), reveal.

Avoid when you cannot obtain real geodata or real documents, when the story needs people the viewer should meet (use
`vox-collage` or `archival-documentary`), or on contested territory where you will not apply one consistent, stated rule.

## Look

Editorial-serif, swiss-grid, newsroom or blueprint; a desk-and-paper variant of `paper-collage` for a warmer tone. One
accent marks the region or line the video is about; everything else is grey (obscuration, 30 to 40% opacity). Documents
shown as real pages with title and date visible (evidence class E0), not as logos.

## Layer mix

code 40 to 85% (maps, route and highlight animation, count-ups, labels, timelines, annotation on documents), real or capture
up to about 40% (document pages, headlines, filings, archival), stock up to 20% for an establishing aerial, ai_image up to
about 30% only for stylised mood or decorative texture, never for a map, border, flag or document. No AI video.

## Beat grammar

News and causal skeletons (`data/intents.json`): date-stamped hook or in medias res anomaly; what happened or the usual answer;
the underlying condition on a map (AND); the trigger (BUT) with the document that shows it; the outcome (THEREFORE); the
"not one cause" or "known versus not known" turn; the one-sentence answer with the hero number or place. A beat names one
place or one document. At most 5 events on a timeline; one highlighted region per map beat; at most 3 numbers per 30 s.

Evidence handling: every claim sourced (primary first), dated; a quote card carries name, role, date and source and is never
cropped out of context; contested topics give each side's strongest claim in its own sourced words, in the same visual
template, with funding or sponsors disclosed; judgments are separated from facts in the voice ("analysts judge").

## Script voice

Sober, specific, present tense for history. Names and places spelled as the audience knows them; pronunciation list for TTS.
Calibrated language for forecasts. No loaded words.

## Motion and edit

Maps: one continuous pan and zoom path between highlights with labels riding the camera, `power2.inOut`, 1.2 to 2.0 s; the
highlight fills and the rest dims; labels land after the camera settles; borders at least 2 px; labels at least 40 px.
Projection by purpose: equal-area for a size comparison, Web Mercator for a city or region zoom, an orthographic globe for a
long route; never switch projection between consecutive beats unless the cut is the point. Choropleth only for rates,
proportional symbols for counts. Documents: zoom to the clause, highlight with a box that draws on, redact what must not
show. Hard cuts at phrase boundaries. Disputed borders and names: choose one stated rule for the whole project.

## Sound

Restrained: a low pulse bed, soft ticks on route and counter events, a riser into the reveal, a hit on the hero number.

## Production route

1. Source collection: documents and headlines captured with their URLs and dates in `claims[]`; geodata from a permissive
   source (public-domain Natural Earth or an open data portal), licence recorded. Probe real files before planning around
   them.
2. Beat map: `code` base with `overlays`, `capture` or `real` for documents; lint; board; Gate 1.
3. Voice, timings. Build maps with d3-geo to SVG paths animated by a seekable GSAP timeline (a D3 transition is not seekable
   in HyperFrames); use `/hyperframes-registry` for map and chart blocks first. Build through `/general-video` with the
   handoff in `11-routing.md`.
4. Contact sheet, safe zones, claims re-check.

## Failure modes

A generated map (borders, labels and scale cannot be trusted); an AI "document" or headline; wrong projection for a size
comparison; Mercator inflation making a country look bigger; a choropleth of raw counts; an outdated border or name without
a stated rule; a quote without date or role; stock footage of the wrong place implying a specific; labels over the platform
rail; a source line missing; flags rendered by an image model (use official SVG assets).

## QA specifics

Every place and document is real and cited; a map beat highlights exactly one region; projection and border rule stated;
numbers traced to claims; source chip on screen for each data or document beat; labels at least 40 px; no AI-generated map,
flag, document or headline in any frame.
