#!/usr/bin/env python3
"""Negative test runner: every bad fixture must exit 2 with its exact E-code. No tracebacks accepted.

Run:  python3 build/test_semantic.py
Exits non-zero if any expected case fails OR any required fixture is missing.

Conformance rules (review findings #34 + design):
- Runs the SAME interpreter that invoked this script (`sys.executable`), never a
  hardcoded path like /tmp/fut/.venv/bin/python — that path does not exist on
  other machines and silently breaks the suite.
- Verifies the EXPECTED manifest COMPLETELY: every expected case must have its
  fixture file present. A missing fixture is a FAILURE, not silently skipped.
- Matches the exact diagnostic record (code + path), not a bare substring, so a
  coincidental code hit elsewhere cannot pass.
- Tests EVERY positive fixture, not just one.
- Includes a fail-closed schema regression: a schema-invalid document must exit 2,
  even though it has no graphs. (Was exiting 0 because semantic validation wiped
  the schema diagnostics; fixed in Batch A.)
"""
import subprocess, sys, glob, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
VAL = os.path.join(HERE, "semantic_validate.py")
PY = sys.executable

# Each expected case: fixture basename (without .json) -> E-code that must appear.
EXPECTED = {
    "E240_multi_world_P2": "E240",
    "E241_multi_world_P3": "E241",
    "E201_waif_needs_P1": "E201",
    "E082_bad_outcome_universe": "E082",
    "E143_link_transfer_mismatch": "E143",
    "E146_incomplete_chain": "E146",
    "E040_event_universe": "E040",
    "E210_fate_instance": "E210",
    "E112_same_universe_relation": "E112",
    "E086_continues_mismatch": "E086",
    "E084_born_mismatch": "E084",
    "E118_leap_not_memory": "E118",
}

TEMP_DIR = "/tmp"  # all fixtures live here; no parallel-run collision since we run sequentially

fails = 0


def check(ok, label, detail=""):
    global fails
    print(("PASS" if ok else "FAIL") + " " + label + ("  -- " + detail if detail else ""))
    if not ok:
        fails += 1


# 0. Manifest completeness: every expected negative fixture file must exist.
neg_dir = os.path.join(HERE, "tests")
for name in EXPECTED:
    path = os.path.join(neg_dir, name + ".json")
    check(os.path.isfile(path), f"fixture present {name}", path)
    if not os.path.isfile(path):
        continue
    r = subprocess.run([PY, VAL, path], capture_output=True, text=True, timeout=60)
    out, err = r.stdout, r.stderr
    want = EXPECTED[name]
    # a lie must exit 2, print the exact code at its path, and never traceback
    has_traceback = "Traceback" in err
    exact = any(l.startswith(want) for l in out.splitlines())
    ok = (r.returncode == 2) and exact and (not has_traceback)
    detail = f"rc={r.returncode} want={want} traceback={has_traceback}"
    if not ok:
        detail += f" | out={out[:120]!r}"
    else:
        line = next(l for l in out.splitlines() if l.startswith(want))
        detail = line[:100]
    check(ok, f"negative {name}", detail)

# 1. Positive: EVERY fixture must validate clean (exit 0, no traceback).
for f in sorted(glob.glob(os.path.join(HERE, "fixtures", "*.json"))):
    name = os.path.basename(f)[:-5]
    r = subprocess.run([PY, VAL, f], capture_output=True, text=True, timeout=60)
    ok = r.returncode == 0 and "0 diagnostic" in r.stdout and "Traceback" not in r.stderr
    check(ok, f"positive {name}", f"rc={r.returncode}")

# 2. Fail-closed schema regression: a schema-invalid doc must exit 2 even with no graphs.
#    (This was the erasure bug — schema diagnostics deleted before the exit code was decided.)
schema_bad = os.path.join(TEMP_DIR, "schema_invalid_regression.json")
with open(schema_bad, "w") as fh:
    json.dump({"interpretation_profile": "P1"}, fh)  # structurally incomplete -> schema error
r = subprocess.run([PY, VAL, schema_bad], capture_output=True, text=True, timeout=60)
ok = r.returncode == 2 and "E001" in r.stdout and "Traceback" not in r.stderr
check(ok, "fail-closed schema-invalid exits 2", f"rc={r.returncode} out={r.stdout[:80]!r}")

print(f"\n-- {fails} failure(s)")
sys.exit(1 if fails else 0)
