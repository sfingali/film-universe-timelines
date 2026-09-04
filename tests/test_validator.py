"""Negative tests: the validator must REFUSE to render lying charts.

Run:  python3 tests/test_validator.py
Exits non-zero if any lie renders.
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "tools", "universe_graph.py")

GOOD = {
    "meta": {"title": "T — Test", "subtitle": "s", "thread_label": "THE THREAD: A → B",
             "footer": "f", "canvas": [2400, 1400]},
    "lanes": [{"id": "B", "label": "B"}, {"id": "A", "label": "A"}],
    "nodes": [{"id": "U1", "lane": "A", "title": "A — The Opening Universe",
               "body": "Where the story begins."}],
    "lanes_content": {
        "A": [{"node": "U1"}, {"split": "10"}, {"stub": "stub-10"},
              {"chip": "A — Runs On", "dim": True}, {"abandon": 80}],
        "B": [{"laneborn": {"from_split": None, "chip": "B — Already Running",
                            "note": "this world began long before the chart"}},
              {"join": "join-10"}, {"abandon": 80}],
    },
    "splits": {"10": {"letter": "10", "caption": "The fork"}},
    "stubs": {"stub-10": {"title": "10B — He Dies", "sub": "dies at #10"}},
    "joins": {"join-10": {"from_split": "10", "to_lane": "B", "side": "left",
                          "label": "he enters B"}},
    "thread": ["U1", "join-10", "ENDING"],
    "legend": ["Every split is permanent."],
}

LIES = {
    "join_listed_in_wrong_lane": ("lanes_content", "A", lambda c: c + [{"join": "join-10"}]),
    "unknown_split_ref":         ("lanes_content", "A", lambda c: c + [{"split": "99"}]),
    "unknown_stub_ref":          ("lanes_content", "A", lambda c: c + [{"stub": "stub-99"}]),
    "unknown_node_ref":          ("lanes_content", "A", lambda c: c + [{"node": "NOPE"}]),
    "join_to_unknown_lane":      ("joins", "join-10", lambda j: {**j, "to_lane": "GHOST"}),
    "join_from_unknown_split":   ("joins", "join-10", lambda j: {**j, "from_split": "99"}),
    "unknown_thread_element":    ("thread", None, lambda t: t + ["GHOST"]),
    "laneborn_unknown_split":    ("lanes_content", "B",
                                  lambda c: [{k: dict(it[k], from_split="99")} if k == "laneborn" else it
                                             for it in c for k in it]),
}


def run_engine(graph, out):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(graph, f)
        path = f.name
    try:
        r = subprocess.run([sys.executable, ENGINE, path, "-o", out],
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr
    finally:
        os.unlink(path)


def deep_copy(g):
    return json.loads(json.dumps(g))


def main():
    failures = 0
    out = os.path.join(tempfile.gettempdir(), "ug-test-out.png")

    # sanity: the good graph must render
    rc, msg = run_engine(deep_copy(GOOD), out)
    if rc != 0:
        print("GOOD GRAPH FAILED TO RENDER — engine broken?")
        print(msg)
        sys.exit(1)
    os.unlink(out)
    print("ok  good graph renders")

    # every lie must exit 2
    for name, mutate in LIES.items():
        g = deep_copy(GOOD)
        key1, key2, fn = mutate
        if key1 == "thread":
            g["thread"] = fn(g["thread"])
        elif key1 == "joins":
            g["joins"][key2] = fn(g["joins"][key2])
        else:
            g[key1][key2] = fn(g[key1][key2])
        rc, msg = run_engine(g, out)
        if rc == 0:
            print(f"FAIL  {name}: lie rendered (exit 0)")
            failures += 1
        elif os.path.exists(out):
            print(f"FAIL  {name}: exit {rc} but PNG exists")
            os.unlink(out)
            failures += 1
        else:
            print(f"ok  {name}: refused (exit {rc})")

    print("ALL PASS" if failures == 0 else f"{failures} FAILURES")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
