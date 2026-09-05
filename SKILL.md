---
name: film-universe-timelines
description: Build Primer-style multi-universe timeline charts for time-travel films — splits, crossings, deaths, no resets.
version: 1.0.0
tags: [film, time-travel, charts, story-development, universes]
repo: https://github.com/sfingali/film-universe-timelines
---

# Film universe timelines

Chart the universe structure of a time-travel / parallel-worlds film as a
publication-grade PNG. Pipeline: **allocation file → compile → render → QA**.
Nothing is ever drawn by hand; the chart is a build artifact.

## The ontology (non-negotiable)

- Every split is permanent. **Never draw a "reset" or rewind arrow.** A "reset"
  is the film following the surviving branch into a *different universe*.
- A split births two tines: the one we follow, and the one where the
  protagonist dies (that one forks RIGHT as a red death stub).
- Joined worlds **backpropagate**: they already existed and were running before
  the protagonist arrives. Draw their lanes from the top of the chart with an
  "already running" chip; the thread enters them at a join dot part-way down.
- A joined lane shows only the time the protagonist occupies it. The world's
  own off-screen life is one grey "elsewhen" tail, not a full biography.
- Time-travel that does NOT fork a world (overwrites, loops, box channels) is
  drawn as ARCS, never lanes: `travel`/`return`/`loop` kinds; another
  character's trip gets its own colour + `carry_through:false` so the film's
  thread ignores it. A genuinely real reset (Groundhog Day) = one lane, loop
  arcs, zero branches — do not fake universes into a reset film.
- Threads split into separate graphs (e.g. another character's jumps, or
  before-lives): separate chart, never mixed into the protagonist's lanes.
- Decide deliberately where the chart ENDS. Ending on the final split keeps a
  world undrawn; that absence can be the point.

Full language: `references/chart-language.md` (in the repo).

## Pipeline

1. **Ground truth first.** Read the screenplay. Number every scene (`#N#`
   markers in fountain). Decide: what splits, what crosses, who dies where.
2. **Write the allocation file** (plain text): lanes left→right (thread flows
   right→left, opening universe RIGHTMOST), scene ranges per lane, crossing
   scenes in story order, non-crossing splits, key beats. Syntax in
   `tools/timeline_compile.py` docstring; worked example in
   `examples/demo-film/demo.universes.txt`.
3. **Compile:** `python3 tools/timeline_compile.py my-film.alloc.txt -o story.universes.json --title "..." --split-name 42:"..."`
4. **Render:** `python3 tools/universe_graph.py story.universes.json -o story.png --style dash`
   (four styles: classic / weight / dash / tape — one JSON renders all).
5. **QA:** vision pass on the full chart (collisions, clipped labels, joins
   dodging text) + pixel checks for stroke styles; negative-test the validator
   (feed it a lie, demand exit 2).

## Hard rules

- Edit the JSON or allocation file, NEVER the PNG. Regenerate instead.
- The validator is law: joins live only in their target lane; unknown ids fail
  the build. Story errors are JSON errors, not drawing bugs.
- Keep the protagonist's lane count minimal — one lane per universe *they
  occupy*, ordered so each crossing hops exactly one lane left.
- Beats carry `#scene` cites so every claim on the chart checks against script.
- Competing ontologies (e.g. "it's a reset") get settled by the director, not
  by the chart. The chart draws the canon; it does not invent it.

## Pitfalls (paid for in debugging)

- Join horizontals must dodge items by full x-extent (stub boxes extend ~400px
  right of their lane) — checking only "lanes between" misses the source lane's
  own stub.
- Thread-through-everything: the green line must carry through nodes, beats,
  chips, splits — initialised at the incoming join y, stopped at the lane's
  last item bottom.
- Duplicate join listings: last-write-wins bugs; use setdefault + explicit dup
  check (the validator does).
- Dash strokes: cell math must be per-cell (t0=kk/nn, width=cell*fraction) —
  whole-segment fractions overpaint and the "dashed" line renders solid.
- Thread only flows DOWN. Drawing carry segments upward puts the protagonist
  in a world before they arrived — a canon violation, not a style choice.
