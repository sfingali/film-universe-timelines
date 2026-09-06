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

ARCS = {
    "a1": {"from_lane": "A", "to_lane": "A", "kind": "loop", "label": "again"},
}
ARC_LIES = {
    "arc_never_departs":  ("no_arc_item", "a1"),
    "arc_never_arrives":  ("no_mark_item", "a1"),
    "arc_from_ghost_lane":("arcs_from_lane", "a1"),
    "arc_bad_kind":       ("arcs_kind", "a1"),
    "arc_bad_color":      ("arcs_color", "a1"),
}

def with_arc(base, arcs=ARCS, arc_items=True, mark_items=True):
    g = deep_copy(base)
    g["arcs"] = deep_copy(arcs)
    if arc_items: g["lanes_content"]["A"].insert(1, {"arc": "a1"})
    if mark_items: g["lanes_content"]["A"].insert(2, {"mark": "a1"})
    return g


# pass 2a additive fields (#2-#6): each must be refused with exit 2, no PNG
PASS2A_LIES = ("interval_no_timescale", "bad_traveller_arc", "bad_traveller_beat",
               "bad_screen", "bad_certainty")

def with_pass2a_lie(base, mode):
    g = deep_copy(base)
    g["meta"]["travellers"] = {"Aaron": [79, 140, 214]}
    if mode == "interval_no_timescale":
        g["arcs"] = {"a1": {"from_lane": "A", "to_lane": "A", "kind": "loop",
                            "label": "again", "interval": [10, 2], "traveller": "Aaron"}}
        g["lanes_content"]["A"].insert(1, {"arc": "a1"})
        g["lanes_content"]["A"].insert(2, {"mark": "a1"})
    elif mode == "bad_traveller_arc":
        g["meta"]["timescale"] = {"unit": "hour", "start": 0}
        g["arcs"] = {"a1": {"from_lane": "A", "to_lane": "A", "kind": "loop",
                            "label": "again", "traveller": "Ghost"}}
        g["lanes_content"]["A"].insert(1, {"arc": "a1"})
        g["lanes_content"]["A"].insert(2, {"mark": "a1"})
    elif mode == "bad_traveller_beat":
        g["lanes_content"]["A"].insert(1, {"beat": "x", "traveller": "Ghost"})
    elif mode == "bad_screen":
        g["lanes_content"]["A"].insert(1, {"beat": "x", "screen": "nonsense"})
    elif mode == "bad_certainty":
        g["lanes_content"]["A"].insert(1, {"beat": "x", "certainty": "nonsense"})
    return g


def with_pass2a_good(base):
    """a well-formed graph opting into every pass2a field — must still render."""
    g = deep_copy(base)
    g["meta"]["timescale"] = {"unit": "hour", "start": 0}
    g["meta"]["travellers"] = {"Aaron": [79, 140, 214]}
    g["meta"]["versioning"] = "crossing-count"
    g["arcs"] = {"a1": {"from_lane": "A", "to_lane": "A", "kind": "loop", "label": "again",
                        "interval": [10, 2], "traveller": "Aaron"}}
    g["lanes_content"]["A"].insert(1, {"mark": "a1"})
    g["lanes_content"]["A"].insert(2, {"beat": "x", "screen": "film", "certainty": "seen",
                                       "traveller": "Aaron"})
    g["lanes_content"]["A"].insert(3, {"arc": "a1"})
    g["lanes_content"]["B"].append({"ending": {"title": "?", "body": "unresolved",
                                               "uncertain": True}})
    return g


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
    # Isolated per-run temp dir: a fixed tempfile path caused parallel-run
    # collisions and a stale PNG from a prior exit-0 negative to fool later tests.
    tmpdir = tempfile.mkdtemp(prefix="ug-test-")
    out = os.path.join(tmpdir, "out.png")

    # sanity: the good graph must render
    rc, msg = run_engine(deep_copy(GOOD), out)
    if rc != 0:
        print("GOOD GRAPH FAILED TO RENDER — engine broken?")
        print(msg)
        sys.exit(1)
    os.unlink(out)
    print("ok  good graph renders")

    # every lie must exit 2 (a crash / traceback / other exit is NOT a pass)
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
        elif rc != 2:
            print(f"FAIL  {name}: wrong exit {rc} (must be 2 for a diagnostic)")
            print("      " + msg[:200])
            failures += 1
        elif os.path.exists(out):
            print(f"FAIL  {name}: exit 2 but PNG exists")
            os.unlink(out)
            failures += 1
        else:
            print(f"ok  {name}: refused (exit 2)")

    # arc lies: each must exit 2
    for name, (how, aid) in ARC_LIES.items():
        if how == "no_arc_item":
            g = with_arc(GOOD, arc_items=False)
        elif how == "no_mark_item":
            g = with_arc(GOOD, mark_items=False)
        elif how == "arcs_from_lane":
            g = with_arc(GOOD); g["arcs"][aid]["from_lane"] = "GHOST"
        elif how == "arcs_kind":
            g = with_arc(GOOD); g["arcs"][aid]["kind"] = "teleport"
        elif how == "arcs_color":
            g = with_arc(GOOD); g["arcs"][aid]["color"] = "red"
        rc, msg = run_engine(g, out)
        if rc == 0:
            print(f"FAIL  {name}: lie rendered (exit 0)")
            failures += 1
        elif rc != 2:
            print(f"FAIL  {name}: wrong exit {rc} (must be 2)")
            print("      " + msg[:200])
            failures += 1
        elif os.path.exists(out):
            print(f"FAIL  {name}: exit 2 but PNG exists")
            os.unlink(out)
            failures += 1
        else:
            print(f"ok  {name}: refused (exit 2)")

    # sanity: a well-formed arc chart must render
    rc, msg = run_engine(with_arc(GOOD), out)
    if rc != 0:
        print("FAIL  well-formed arc chart refused:")
        print(msg)
        failures += 1
    else:
        os.unlink(out)
        print("ok  well-formed arc chart renders")

    # pass 2a lies: each must exit 2, no PNG
    for mode in PASS2A_LIES:
        g = with_pass2a_lie(GOOD, mode)
        rc, msg = run_engine(g, out)
        if rc == 0:
            print(f"FAIL  {mode}: lie rendered (exit 0)")
            failures += 1
        elif rc != 2:
            print(f"FAIL  {mode}: wrong exit {rc} (must be 2)")
            print("      " + msg[:200])
            failures += 1
        elif os.path.exists(out):
            print(f"FAIL  {mode}: exit 2 but PNG exists")
            os.unlink(out)
            failures += 1
        else:
            print(f"ok  {mode}: refused (exit 2)")

    # sanity: a well-formed graph using every pass2a field must still render
    rc, msg = run_engine(with_pass2a_good(GOOD), out)
    if rc != 0:
        print("FAIL  well-formed pass2a chart refused:")
        print(msg)
        failures += 1
    else:
        os.unlink(out)
        print("ok  well-formed pass2a chart renders")

    print("ALL PASS" if failures == 0 else f"{failures} FAILURES")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
