# Chart JSON schema

The JSON is the story. The engine validates then renders. Version: v4 engine.

```jsonc
{
  "_doc": "optional note; ignored",
  "meta": {
    "title": "THE FILM — One Man's Story",
    "subtitle": "one line under the title",
    "thread_label": "THE THREAD: OPEN → WORLD B → WORLD C — THE LAST PULL",
    "footer": "small grey line at the very bottom",
    "canvas": [2800, 3600],            // width clamped to >= 2400
    "node_types": {                    // OPTIONAL per-film palette
      "death":  {"color": [150,74,74]},   // stub edge; fill+text derived
      "ending": {"color": [38,118,62]},   // ending box edge
      "split":  {"color": [255,232,122], "edge": [185,168,95], "text": [60,48,8]},
      "thread": {"color": [38,118,62], "weight": 10},
      "lane":   {"color": [150,148,142], "weight": 4},
      "join":   {"color": [38,118,62], "weight": 10}
    }
  },
  "lanes": [ {"id": "FAM", "label": "FAM"}, ... ],   // LEFT to RIGHT
                                                     // opening universe RIGHTMOST;
                                                     // thread flows right -> left
  "nodes": [ {                        // story-start box, in the opening lane
    "id": "U1", "lane": "OPEN",
    "title": "OPEN — The Opening Universe",
    "body": "Where the story begins.",
    "cite": "p1 #1–3"                 // optional
  } ],
  "lanes_content": {                  // per lane, TOP to BOTTOM, in draw order
    "OPEN": [
      {"node": "U1"},
      {"split": "10"},                // must exist in splits{}
      {"beat": "scene 16", "cite": "#16"},          // optional: tone death|good, side left
      {"segment": "THE TIMELINE WITH HER (from the join down)"} // green chip
      {"stub": "stub-10"},            // the death tine box (forks right)
      {"chip": "OPEN — Runs On", "dim": true},
      {"abandon": 140}                // px of faded 'runs on' tail (60..320)
    ],
    "HER": [
      {"laneborn": {"from_split": null,              // null = already running
        "chip": "HER — Already Running",
        "note": "this world began long before the chart"}},
      {"join": "join-78"}             // join item lives ONLY in to_lane's list
    ]
  },
  "splits": { "10": {"letter": "10", "caption": "The crash — the worlds split"} },
  "stubs":  { "stub-10": {"title": "10B — He Dies", "sub": "the tine where he dies at split #10"} },
  "joins":  { "join-78": {"from_split": "10", "to_lane": "HER",
                           "side": "left", "label": "he enters HER"} },
  "thread": ["U1", "join-78", "ENDING"],   // ordered route; ids must resolve;
                                           // 'ENDING' is a literal
  "legend": ["line one", "line two"]       // 'The Index / How to Read' box
}
```

## Validation rules (enforced, exit 2)

- every `split`/`stub`/`node`/`join` reference in `lanes_content` must resolve
- a `join` item may be listed in **only one** lane, and it must be the join's
  `to_lane`
- `joins.*.from_split` must exist; `to_lane` must be a real lane
- every `thread` element must be a known node/split/join id or `ENDING`
- unknown lanes in `lanes_content` fail

## Optional items

- `{"ending": {"title": "...", "body": "...", "cite": "#277–278"}}` in a lane's
  content — green final-image box (hmm: see `universe_graph.py` measure()).
- `{"tone": "death"|"good"}` on beats colours the dot.
- `{"side": "left"}` on beats/joins flips the label to the other side of the
  lane line; join labels auto-flip if they would clip the canvas edge.
