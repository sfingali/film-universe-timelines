# Reference timelines — prior art

Timelines other people built for Primer and Back to the Future, collected as
prior art for the next redesign. All fan-made, credited to their makers.
Mirror rule: each entry lists its live source — follow the links for the
author's latest version.

## Primer

| file | author / source | structure | steal-worthy |
|------|-----------------|-----------|--------------|
| `primer/unrealitymag-flowchart.jpg` (2791×1745) | [Unreality Magazine flowchart](https://www.unrealitymag.com) — the chart Stephen wanted | horizontal river of branches, colour per copy | the "copies as parallel swimmers" read; minimal text per node |
| `primer/clawz114-6k-grid.png` (6000px+) | u/Clawz114, [Reddit grid version](https://www.reddit.com/r/primer/) | dense grid, every box run enumerated | completeness — every trip and counter-trip is on it; the ceiling of the exhaustive approach |
| `primer/wikipedia-timelines.gif` | [Wikipedia: Primer (film) — Plot](https://en.wikipedia.org/wiki/Primer_(film)) | small multiples of the four plot stages | compression: four frames instead of one monster |

What they all dodge: which Aaron is narrating, and what the fail-safe exit
does to the counting. Our `examples/primer/` JSON is the simplified-honest
position; the 6K grid is the exhaustive position.

## What the Primer charts teach (studied at full resolution, 2026-09-05)

Three charts, three trade-offs, eight transferable lessons:

1. **Rotate the axes.** All three independently chose HORIZONTAL time with
   timeline rows stacked top→bottom (Timeline 1 at top, 9/11+ below). Our
   engine draws vertical lanes; for channel-grammar films the rotated layout
   is the native form — a new generation is a new ROW, and a box run is a
   loop WITHIN a row. Candidate feature: `--orientation horizontal`.
2. **Box runs are loop-rectangles, not elbow arcs.** Clawz114 draws each run
   as a small rectangle ON the row: enter at exit-time, the rectangle encloses
   the box's interior duration, the line re-emerges EARLIER and continues
   right. The box's 6 hours are geometry — you can measure the trip. Our
   left-bulging arcs show direction but hide duration. Better primitive for
   `loop`/`travel` arcs: `interval: [depart_time, arrive_time]` renders the
   staple shape.
3. **Versions numbered by crossing count.** `Aaron(0)`, `Aaron(1)`,
   `Aaron(2)` — the number is how many trips that copy has made. Boxes get
   versioned too (`Box A(0)`, `FailSafe(0)`). We have no per-person version
   counter; `meta.versioning: "crossing-count"` would give the engine a
   namespace rule instead of hand-labelled lanes.
4. **Screen-presence chips.** UnrealityMag marks where the FILM actually shows
   you something: yellow chips — "This is seen in the movie", "seen as
   flashback", "seen in the first bench scene" — pinned to the true timeline.
   The film presents Timeline 9 linearly; the chart maps presentation order
   onto real structure. Add `screen: "film"|"flashback"|"deduced"` to beats.
5. **Narration pinned to a version.** UnrealityMag handles the unresolvable
   narrator question with one chip: "This is seen when narrator Aaron(2)
   recalls the event in phone call." Don't resolve the ambiguity — attribute
   the telling.
6. **Epistemic colour-coding.** Clawz114's notes are coloured by HOW YOU KNOW:
   grey = seen in the film; blue = seen as flashback, after the event;
   green = seen in the film but in a LATER timeline; red = not seen, explained
   or becomes apparent later. The chart asserts its evidence status per note —
   the same discipline as the evidence-not-assertions wiki rule. Maps to a
   `certainty` field per beat.
7. **Runtime cites + honesty rows.** Clawz114 cites the film's runtime
   (46:32, 1:09:18) where scene numbers don't exist, compresses the
   uncountable party attempts into a row labelled "Timeline 11+", and ends on
   a row labelled "?" — the unknowable final state. Uncertainty gets its own
   row, not a guess.
8. **The survivor census.** His closing note computes the ending's cost:
   "At the end of the film, there are 2× Abes and 3× Aarons living
   permanently on the same timeline." A validator could emit this for any
   chart — count copies alive at the ending, print it in the legend.

Trade-off summary: UnrealityMag is the narrative map (prose on structure),
Clawz114 is the proof (complete, evidence-coloured, runtime-cited), Wikipedia
is the gesture (whole film in one glance, no events). A redesign can be all
three: Clawz114's rigour, UnrealityMag's chips, Wikipedia's single screen.

## Back to the Future (trilogy / Part II)

| file | author / source | structure | steal-worthy |
|------|-----------------|-----------|--------------|
| `bttf2/reddit-trilogy-diagram.png` | u/Steph_eN17 — [reddit thread](https://www.reddit.com/r/BacktotheFuture/comments/1oznoy5/) · [image](https://i.redd.it/t2dtyqa2zu1g1.png) | 13 numbered trips as arrows between year columns (1885/1955/1985/2015), time-circuit dashboard panels with exact FROM/TO datetimes | the RIGHT panel — datetimes as first-class data; year columns not lanes; trips numbered in story order |
| `bttf2/clickhole-all-timelines.jpg` (2000×6985) | [ClickHole](https://www.clickhole.com/2016/08/04/so-cool-this-chart-visualizes-every-timeline-in-back-1825122210) — satirical | stacked TIMELINE 0–7 bands, dotted arcs per traveller, colour legend per character, annotations per band | band-per-timeline instead of lane-per-universe; per-traveller colour (our `arcs[].color`); the annotation prose under each band |
| `xkcd-movie-narrative-charts.png` | [xkcd #657](https://xkcd.com/657/) (Primer is in the Primer/Lord of the Rings panel set) | character lines through scene-time, vertical bars for off-screen | vertical = FILM time (scene order), not world time — the axis choice that makes Primer chartable at all |

## Redesign notes (what to take into the engine)

1. **Two axes, never confused.** Fan charts that work put FILM-TIME vertical
   (or story order left→right) and WORLD identity in colour/bands. Our engine
   currently puts world-time vertical; the ClickHole bands + xkcd scene-axis
   are the alternatives worth a `--style`.
2. **Datetimes are data.** The Reddit diagram's FROM/TO panels are the single
   best idea: every arc could carry `depart:`/`arrive:` datetimes rendered as
   a time-circuit chip.
3. **Per-traveller colour.** ClickHole colours by character; our arcs already
   support per-arc colour — make travellers a first-class concept
   (`meta.travellers: {"name": "color"}`) so arcs inherit automatically.
4. **Bands vs lanes.** Stacked timeline bands (ClickHole) read better for
   overwrite grammars than vertical lanes, because the whole band is the
   world-state at one generation. Candidate style: `bands`.
5. **Numbered story order.** The Reddit diagram numbers trips 1–13; our arcs
   are unnumbered. Cheap win: render story-order badges on arc departures.
