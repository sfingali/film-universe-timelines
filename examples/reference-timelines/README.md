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
