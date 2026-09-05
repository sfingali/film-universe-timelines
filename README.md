# film-universe-timelines

Primer-style universe timeline charts for films that deal with time travel and
multiple universes. Declarative: you describe the **story** (lanes, splits,
crossings, deaths) in a JSON file or a plain-text allocation file; the engine
computes the geometry and renders publication-grade PNGs in four styles.

Built for THE WAIF (Stephen Fingleton), generalised for any multi-universe film.

![demo chart](examples/demo-film/demo-classic.png)

## The one rule

**Never draw a "reset".** Every split is permanent. A time-travel act splits the
world in two: one branch where the traveller dies (or fails), one where they
continue. What reads on screen as a rewind is the film following the surviving
branch *into a different universe*. Worlds the traveller joins **already
existed** and were running before they arrived — draw their lanes from the top
of the chart. Full ontology in [`references/chart-language.md`](references/chart-language.md).

## Quick start

```bash
pip install pillow

# 1. describe your film's scenes per universe (plain text, see references/method.md)
#    a worked synthetic example ships in examples/demo-film/demo.universes.txt

# 2. compile it to the chart JSON
python3 tools/timeline_compile.py examples/demo-film/demo.universes.txt \
    -o demo.universes.json \
    --title "THE MIDNIGHT TOWER — One Man's Story" \
    --split-name 7:"He jumps the turnstile — the worlds split"

# 3. render
python3 tools/universe_graph.py demo.universes.json -o demo.png --style dash
```

Or skip the compiler and write the JSON directly — see
[`references/json-schema.md`](references/json-schema.md).

## The four styles

| style    | grammar                                                                 |
|----------|-------------------------------------------------------------------------|
| `classic`| the reference look — heavy green thread, yellow split circles            |
| `weight` | stroke hierarchy — thread heaviest, deaths hairline                      |
| `dash`   | dashed = pre-history / death. Dash carries the backpropagation meaning   |
| `tape`   | transit-map grammar — 45° bends, no arrowheads, flat ink                 |

One JSON renders all four:

```bash
for st in classic weight dash tape; do
  python3 tools/universe_graph.py demo.universes.json -o demo-$st.png --style $st
done
```

## Visual language

- vertical lanes = universes (left→right order set by you)
- **yellow split circle** = a branching act, carrying the scene number
- **red stub box** = the tine where the protagonist dies (forks right, diagonal)
- **green dot + horizontal** = a crossing: the survivor enters an
  already-running world (drawn down-then-across, never a rewind arrow)
- **grey "ALREADY RUNNING" chip** at a lane's top = that world predates the traveller
- **blue "RUNS ON" chip + faded tail** = the abandoned branch keeps existing
- the **green thread** is the film's path — one continuous line, start to ending
- **time-travel arcs** (elbow curves) = a trip within or into worlds *without a
  new universe*: `travel` (thread colour), `return` (grey), `loop` (lane colour,
  e.g. Groundhog Day's day-reset). Another character's trip (old Biff) draws in
  its own colour with `carry_through: false` — the film's thread ignores it.

Per-film colours: set `meta.node_types` (e.g. `{"death": {"color": [40,40,160]}}`)
and every derived shade (fill, text) follows.

## The four grammars (test films)

| film | grammar | what the chart proves |
|------|---------|----------------------|
| THE WAIF (private) | split/join | every pull splits; joined worlds pre-exist |
| Back to the Future Part II | overwrite + one true branch | revisions in place on ONE lane; alt-1985 alone is a new world |
| Groundhog Day | the real reset | one lane, zero branches — the honest anti-universe chart |
| The Butterfly Effect | chain | each dive rewrites a life: new lane, abandoned lives run on |
| Primer | channel | the box rides inside one world-line: out late, in earlier |

All four example JSONs ship in `examples/` — read them as cookbooks.

## Spec v2.3 — the flexible world model (new)

Below the v1 chart engine, the repo now carries **spec v2.3**: a validated
data model that can express time-travel ontologies beyond split/join —
branch multiverse (P1), single mutable timeline (P2), closed loop (P3),
undeclared (P4) — plus named film presets (`tenet`, `dark`, `steins-gate`,
`looper`, `memento`, …). The spec was designed, amended and adversarially
attacked by an LLM reviewer, then executed: schema, validator, six film
fixtures, rendered charts.

**The interpretation profile is law.** Every v2.3 document declares its
ontology up front; the validator rejects documents whose machinery contradicts
it (P2/P3 must not contain split/join machinery; `waif` rules require P1).
The renderer prints the profile on every chart so the ontology being asserted
is never silent.

### The pipeline

```
fixture JSON (v2.3) -> build/schema_v2.json (frozen contract, 69 defs)
                    -> build/semantic_validate.py (E-series invariants, exit 2 on violation)
                    -> build/v23_adapter.py -> tools/universe_graph.py --fixture -> PNG
```

### Commands

```bash
# validate a fixture (schema + semantics)
python3 build/semantic_validate.py build/fixtures/bens_story.json

# render it
python3 tools/universe_graph.py build/fixtures/tenet.json --fixture --out build/render

# run the negative test suite (12 lying documents must each fail with their exact code)
python3 build/test_semantic.py
```

### The six executed fixtures

| film | profile | what it proves |
|------|---------|----------------|
| Ben's Story (THE WAIF) | P1 + waif | full canon topology validates unchanged: born/preexisting origins, per-tine outcomes, consciousness transfers, namespace isolation |
| Groundhog Day | P3 | one world, iterations as revisions, memory-only persistence — no P1 machinery |
| Back to the Future Part II | P2 | alt-1985 as a superseded revision, not a universe |
| Tenet | tenet | inverted strands as lanes, turnstile crossings, the pincer |
| Dark | dark | era lanes, cave crossings, the Charlotte/Elisabeth bootstrap pair |
| Steins;Gate | steins-gate | divergence-metric revisions, Reading Steiner memory-only traversal |

All six validate with zero diagnostics; renders in `build/render/`.

### Honesty rules

- The validator never invents facts — where the film gives no evidence the
  fixture records `status: "unavailable"` and states the gap.
- A fixture that cannot satisfy an invariant does not get the invariant
  weakened silently; it goes to `build/OPEN_ISSUES.md` with its diagnostic.
- Known open issues: E257/E258 (Tenet boundary + pincer semantics), P2
  simultaneity costs, genealogy-cycle rendering, divergence constraints.

### Documents

- `build/SPEC_v23.md` — the four-part spec (v2 base, v2.1 profiles, v2.2
  parametric integration, v2.3 adversarial repairs R1–R11)
- `build/REPORT.md` — implementation report
- `build/OPEN_ISSUES.md` / `build/CHANGELOG.md` — gaps and changes

## Design principles

1. **Ground truth ≠ drawing.** The story lives in data; geometry is computed;
   story errors are validation errors, not drawing bugs. The engine refuses to
   render an inconsistent graph (exit 2, no PNG).
2. **Fixed-point layout.** Joins anchor below their source split and everything
   flows down from there; the layout iterates until stable, so nothing is
   clipped and no lane cursor goes stale.
3. **Hand-editing PNGs is forbidden.** Edit the JSON (or the allocation file)
   and recompile. The chart is a build artifact.
4. **Cite the script.** Every beat carries `#scene` numbers so notes can be
   checked against the screenplay.

## Repo layout

```
tools/universe_graph.py     render engine (validator + fixed-point layout + 4 styles + --fixture mode)
tools/timeline_compile.py   plain-text scene allocations -> chart JSON
build/schema_v2.json        frozen v2.3 executable JSON Schema (R1)
build/semantic_validate.py  v2.3 semantic validator (E-series invariants)
build/v23_adapter.py        v2.3 fixture -> render-engine adapter
build/fixtures/             six executed film fixtures (validate rc=0)
build/render/               rendered charts
build/test_semantic.py      negative suite: 13/13
build/SPEC_v23.md           the spec (design + adversarial history)
build/REPORT.md             implementation report
build/OPEN_ISSUES.md        known gaps, honestly logged
references/                 chart language (ontology), JSON schema, production method
examples/                   hand-curated v1 cookbooks (bttf2, primer, demo-film, …)
tests/                      v1 negative tests: a lying chart must fail loudly
```

## Origin

The engine was built to chart THE WAIF's universe structure — four splits,
three crossings, no resets — after tiling together the fan-made Primer charts
(unrealitymag flowchart, the Clawz114 6K grid, the Wikipedia GIF). The Waif
files themselves are not in this repo; `examples/demo-film/` is a synthetic
film that exercises the same features.

## License

MIT — see [LICENSE](LICENSE).
