#!/usr/bin/env python3
"""universe_graph.py — declarative render engine for film universe charts.
Story lives in JSON; geometry is COMPUTED; styles are params. Film-agnostic:
nothing here knows the movie. v4 layout core = fixed-point restack (see history below).

v4 — layout core rewritten as a FIXED-POINT RESTACK (audit 2026-09-03 + render QA):
  * no two-pass provisional/shift: every pass stacks lanes in order, placing joins
    IN-FLOW at yj = max(stack cursor + clearance, source_split_y + JOIN_DROP),
    then content continues below the join dot. Iterate until stable (≤8 passes).
  * => join connectors always run DOWN from the source split then across;
    => a lane's post-join content always sits BELOW the join (narrative order);
    => lane cursors and canvas height are always consistent (nothing clipped).
  * join horizontals DODGE text on lanes they cross (shift down to clear band).
  * join labels auto-flip right when they would clip off the left edge.
  * vertical rhythm BREATHE-scaled (airier, closer to the approved v5 hand-built look).
  * abandon tails always render (world "runs on" even after the thread departs).
  * engine VALIDATES the JSON first: joins must live in to_lane, thread must resolve,
    unknown ids fail loudly. Story errors are JSON errors, not drawing bugs.
Connector grammar (approved v5 look):
  lane pre-history: grey from lane top (already-running lanes) or from birth split (born lanes)
  thread (green):   the film's path; a split with an outgoing join ENDS the carry
  join draw:        vertical down the SOURCE lane from the split, horizontal across,
                    green dot on the target lane, green continues below the dot
  deaths:           diagonal from split to stub box right of the lane, X/square cap
Usage: python3 universe_graph.py graph.json [-o out.png] [--style classic|weight|dash|tape]
"""
import json, math, os, re, sys, argparse
from PIL import Image, ImageDraw, ImageFont

def _find_font(name):
    for base in ("/usr/share/fonts/truetype/dejavu",
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
                 os.path.expanduser("~/.fonts")):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None

def F(sz, bold=False, mono=False):
    n = "DejaVuSansMono.ttf" if mono else ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    p = _find_font(n)
    if p:
        return ImageFont.truetype(p, sz)
    return ImageFont.load_default()

def wrap_fn(dd):
    def tw(t, f): return dd.textlength(t, font=f)
    def wrap(t, f, maxw):
        words, lines, cur = t.split(), [], ""
        for w0 in words:
            trial = (cur+" "+w0).strip()
            if tw(trial, f) <= maxw: cur = trial
            else:
                if cur: lines.append(cur)
                cur = w0
        if cur: lines.append(cur)
        return lines
    return tw, wrap

_SMALL = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on", "or",
          "the", "to", "with", "from", "into"}
_PROTECT = set()   # all-caps tokens preserved verbatim (lane ids/labels — acronyms)

def _cap_word(w):
    m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z']*)(.*)$", w)
    if not m:
        return w
    pre, core, suf = m.groups()
    core = core[0].upper() + core[1:].lower()
    if suf.startswith("'") and len(suf) >= 2:
        suf = "'" + suf[1].upper() + suf[2:]
    return pre + core + suf

def tc(s):
    """House rule: chart lettering reads as hand-lettered — title-case ALL-CAPS strings."""
    if not isinstance(s, str) or not s or not s.isupper():
        return s
    words = s.split()
    out = []
    for i, w in enumerate(words):
        if w.upper() in _PROTECT:
            out.append(w)
            continue
        lw = w.lower().strip("—-·,.:;()[]")
        prev_break = i > 0 and s.split()[i-1].strip("·,.:;()[]") in ("—", "--", "-", "/")
        if 0 < i < len(words) - 1 and lw in _SMALL and not prev_break:
            out.append(w.lower())
        else:
            out.append(_cap_word(w))
    return " ".join(out)

# ---------------- validation ----------------
def validate(g):
    errs = []
    lane_ids = [l["id"] for l in g.get("lanes", [])]
    if not lane_ids: errs.append("lanes: empty")
    lc = g.get("lanes_content", {})
    for lid in lc:
        if lid not in lane_ids: errs.append(f"lanes_content: unknown lane '{lid}'")
    node_ids = {n_["id"] for n_ in g.get("nodes", [])}
    stubs = g.get("stubs", {})
    splits = g.get("splits", {})
    joins = g.get("joins", {})
    join_lanes = {}
    for lid in lane_ids:
        for it in lc.get(lid, []):
            k = next(iter(it))
            if k == "node" and (it[k] not in node_ids):
                errs.append(f"{lid}: unknown node '{it[k]}'")
            elif k == "stub" and (it[k] not in stubs):
                errs.append(f"{lid}: unknown stub '{it[k]}'")
            elif k == "split" and (it[k] not in splits):
                errs.append(f"{lid}: unknown split '{it[k]}'")
            elif k == "join":
                jid = it[k]
                if jid not in joins: errs.append(f"{lid}: unknown join '{jid}'")
                else:
                    prev = join_lanes.setdefault(jid, lid)
                    if prev != lid:
                        errs.append(f"{lid}: join '{jid}' listed in multiple lanes "
                                    f"('{prev}' and '{lid}') — place it only in to_lane")
    for jid, j in joins.items():
        if not isinstance(j, dict) or "to_lane" not in j or "from_split" not in j:
            errs.append(f"joins.{jid}: needs from_split and to_lane")
            continue
        if j["to_lane"] not in lane_ids:
            errs.append(f"joins.{jid}: unknown to_lane '{j['to_lane']}'")
        elif join_lanes.get(jid) not in (None, j["to_lane"]):
            errs.append(f"joins.{jid}: listed in lane '{join_lanes[jid]}' but to_lane is "
                        f"'{j['to_lane']}' — place the join item only in to_lane")
        if j["from_split"] not in splits:
            errs.append(f"joins.{jid}: unknown from_split '{j['from_split']}'")
    for lb_lane in lane_ids:
        for it in lc.get(lb_lane, []):
            k = next(iter(it))
            if k == "laneborn":
                fs = it[k].get("from_split")
                if fs is not None and fs not in splits:
                    errs.append(f"{lb_lane}.laneborn: unknown from_split '{fs}'")
    timescale = g.get("meta", {}).get("timescale")
    travellers = g.get("meta", {}).get("travellers")
    versioning = g.get("meta", {}).get("versioning")
    if versioning is not None and versioning != "crossing-count":
        errs.append(f"meta.versioning: unknown value '{versioning}' (only 'crossing-count' supported)")
    if travellers is not None and not isinstance(travellers, dict):
        errs.append("meta.travellers: must be an object of name -> [r,g,b]")
    for name, col in (travellers or {}).items():
        if not (isinstance(col, list) and len(col) == 3):
            errs.append(f"meta.travellers.{name}: color must be [r,g,b]")
    known_travellers = set((travellers or {}).keys())

    arcs = g.get("arcs", {})
    arc_items, mark_items = [], []
    for lid in lane_ids:
        for it in lc.get(lid, []):
            k = next(iter(it))
            if k == "arc":
                if it[k] not in arcs: errs.append(f"{lid}: unknown arc '{it[k]}'")
                else: arc_items.append((lid, it[k]))
            elif k == "mark":
                if it[k] not in arcs: errs.append(f"{lid}: unknown mark '{it[k]}' (marks belong to arcs)")
                else: mark_items.append((lid, it[k]))
    placed = [aid for _, aid in arc_items]
    if len(placed) != len(set(placed)):
        errs.append("an arc item is placed more than once (each arc has exactly one departure)")
    for aid, a in arcs.items():
        if a.get("from_lane") not in lane_ids:
            errs.append(f"arcs.{aid}: unknown from_lane '{a.get('from_lane')}'")
        if a.get("to_lane") not in lane_ids:
            errs.append(f"arcs.{aid}: unknown to_lane '{a.get('to_lane')}'")
        if a.get("kind") not in (None, "travel", "return", "loop"):
            errs.append(f"arcs.{aid}: kind must be travel|return|loop")
        if "color" in a and (not isinstance(a["color"], list) or len(a["color"]) != 3):
            errs.append(f"arcs.{aid}: color must be [r,g,b]")
        for flag in ("carry_through", "arrive_thread"):
            if flag in a and not isinstance(a[flag], bool):
                errs.append(f"arcs.{aid}: {flag} must be boolean")
        if "interval" in a:
            iv = a["interval"]
            if not (isinstance(iv, list) and len(iv) == 2 and all(isinstance(x, (int, float)) for x in iv)):
                errs.append(f"arcs.{aid}: interval must be [depart, arrive] numbers")
            if not timescale:
                errs.append(f"arcs.{aid}: interval requires meta.timescale to be set")
        if "traveller" in a and a["traveller"] not in known_travellers:
            errs.append(f"arcs.{aid}: traveller '{a['traveller']}' not declared in meta.travellers")
    for lid in lane_ids:
        for it in lc.get(lid, []):
            k = next(iter(it)); v = it[k]
            if k == "beat":
                if "screen" in it and it["screen"] not in ("film", "flashback", "deduced"):
                    errs.append(f"{lid}: beat screen must be film|flashback|deduced (got '{it['screen']}')")
                if "certainty" in it and it["certainty"] not in ("seen", "flashback", "seen-later", "never-shown"):
                    errs.append(f"{lid}: beat certainty must be seen|flashback|seen-later|never-shown (got '{it['certainty']}')")
                if "traveller" in it and it["traveller"] not in known_travellers:
                    errs.append(f"{lid}: beat traveller '{it['traveller']}' not declared in meta.travellers")
            if k == "ending" and isinstance(v, dict):
                if "uncertain" in v and not isinstance(v["uncertain"], bool):
                    errs.append(f"{lid}: ending.uncertain must be boolean")
    placed_set, marked_set = set(placed), set(a for _, a in mark_items)
    if len(mark_items) != len(marked_set):
        errs.append("a mark is placed more than once (each arc has exactly one arrival)")
    for aid in arcs:
        if aid not in placed_set: errs.append(f"arcs.{aid}: never departs — place its arc item in from_lane")
        if aid not in marked_set: errs.append(f"arcs.{aid}: never arrives — place its mark item in to_lane")
    for _, aid in mark_items:
        if aid not in arcs: errs.append(f"mark '{aid}' has no arc definition")
    known = set(node_ids) | set(splits) | set(joins) | set(arcs) | {"ENDING"}
    for t in g.get("thread", []):
        if t not in known: errs.append(f"thread: unknown element '{t}'")
    return errs

# ---------------- layout + draw ----------------
def build(g, style="classic", density="normal", orientation="vertical", hitboxes=None):
    global _PROTECT
    _PROTECT = set()
    compact = density == "compact"
    horiz = orientation == "horizontal"

    def XY(t, n):
        """The single transpose (brief pass2b #1): every drawn coordinate is a
        lane-relative (t=position-along-lane, n=offset-across-lane) pair until
        this function turns it into a screen (x,y). vertical: (x,y)=(n,t).
        horizontal: (x,y)=(t,n). Nothing downstream of this function should
        need to know which orientation is active."""
        return (t, n) if horiz else (n, t)

    for l in g.get("lanes", []):
        _PROTECT.add(str(l.get("id", "")).upper())
        lab = str(l.get("label", "")).strip()
        if lab and lab.isupper() and len(re.findall(r"[A-Za-z0-9*']+", lab)) == 1:
            _PROTECT.add(re.findall(r"[A-Za-z0-9*']+", lab)[0].upper())
    W = max(int(g["meta"]["canvas"][0]), 2400)
    MARGIN, LANE_GAP = 60, (78 if compact else 100)
    lane_ids = [l["id"] for l in g["lanes"]]
    n = len(lane_ids)
    LANE_W = min(560, (W - 2*MARGIN - (n-1)*LANE_GAP)//n)
    total = n*LANE_W + (n-1)*LANE_GAP
    HEADER = 230   # px of screen-Y the title/subtitle/thread-label chrome occupies
    # lane axis (n) starts after the header when it's the screen-Y axis (horizontal);
    # the flow axis (t) starts after the header when it's the screen-Y axis (vertical).
    x0 = HEADER if horiz else (W-total)//2
    X = {lid: x0 + i*(LANE_W+LANE_GAP) for i, lid in enumerate(lane_ids)}
    Y_TOP = MARGIN if horiz else HEADER

    probe = Image.new("RGB",(10,10)); dd = ImageDraw.Draw(probe)
    tw, wrap = wrap_fn(dd)
    f_body=F(18); f_node=F(20,bold=True); f_cap=F(17,bold=True); f_seg=F(16,bold=True)
    f_chip=F(17,bold=True); f_note=F(18); f_beat=F(16); f_cite=F(14,mono=True)

    nodes = {n_["id"]: n_ for n_ in g.get("nodes", [])}
    stubs = g.get("stubs", {})
    raw = {lid: list(g.get("lanes_content", {}).get(lid, [])) for lid in lane_ids}

    # survivor census (#7): computed occupancy, appended to legend iff meta.travellers exists
    travellers_meta = g.get("meta", {}).get("travellers")
    census_line = None
    if travellers_meta:
        counts = {name: 1 for name in travellers_meta}
        for a_ in g.get("arcs", {}).values():
            tvl = a_.get("traveller")
            if tvl in counts:
                counts[tvl] += 1
        census_line = ", ".join(f"{counts[name]}× {name}" for name in travellers_meta) + " alive at the ending"
    legend_lines = list(g.get("legend", [])) + ([census_line] if census_line else [])

    B = 1.02 if compact else 1.35   # vertical breathing factor
    STUB_OFF = 60 if compact else 92
    JOIN_DROP = 120   # px below the source split center for the join horizontal
    PX_PER_UNIT = 30  # interval (#2): px per meta.timescale unit for loop-rectangle height
    SLOTS = dict(beat=round(56*B), segment=round(70*B), chip=round(66*B),
                 split=round(132*B), join_after=round(118*B),
                 laneborn=round(150*B), node_gap=round(26*B), stub_gap=round(16*B)+10,
                 arc=round(70*B), mark=round(60*B),
                 ending_gap=round(30*B), abandon_gap=round(26*B))
    if horiz:
        # In horizontal mode these slot sizes advance the cursor along the flow
        # axis (screen-x), which is also where each item's own label/text is
        # drawn (reading left to right) — so the slot has to be wide enough to
        # hold the label itself, not just a narrow vertical-rhythm gap.
        for k_ in ("beat", "chip", "segment", "laneborn", "split", "join_after", "arc", "mark"):
            SLOTS[k_] = max(SLOTS[k_], 260 if k_ in ("laneborn", "split") else 220)

    def measure(kind, v, lid):
        """(w, h) of the item's visual box at cx (x-center of its lane)."""
        cx = X[lid]
        if kind == "node":
            nv = nodes[v] if isinstance(v, str) else v
            lines = wrap(nv["body"], f_body, LANE_W-30)
            return LANE_W, 12+28+22*len(lines)+(22 if nv.get("cite") else 0)+12
        if kind == "stub":
            sv = stubs[v] if isinstance(v, str) else v
            lines = wrap(sv.get("sub",""), f_body, 390)
            return 400, 12+28+22*len(lines)+12
        if kind == "ending":
            lines = wrap(v["body"], f_body, 640)
            return 660, 12+28+22*len(lines)+(22 if v.get("cite") else 0)+12
        return 0, 0

    def q_extent_any(q):
        """logical (n-extent, t-extent) of a placed item (build scope — used by arc routing).
        node/stub/ending always RENDER upright at fixed (w=LANE_W-ish, h=content-driven)
        screen size regardless of orientation (text can't rotate), so their logical
        t/n footprint swaps w<->h in horizontal mode — the one axis-conditional this
        engine needs (brief pass2b: "text wrap widths...genuinely impossible" to transpose)."""
        k2 = q["kind"]; qx, ql = q["cx"], q["w"]
        if k2 in ("node", "stub", "ending"):
            return (qx, qx+q["h"], q["y"], q["y"]+q["w"]) if horiz else (qx, qx+ql, q["y"], q["y"]+q["h"])
        if k2 == "split":
            sl2 = g["splits"][q["v"]]
            return (qx-30, qx+44+tw(sl2["caption"].split("\n")[0], f_cap),
                    q["y"]-30, q["y"]+30)
        if k2 == "chip":
            cv = q["v"] if isinstance(q["v"], dict) else {"chip": q["v"]}
            clines = wrap(tc(cv["chip"]), f_chip, LANE_W-30)
            return (qx+16, qx+16+max(tw(l, f_chip) for l in clines)+20, q["y"], q["y"]+30*len(clines))
        if k2 == "segment":
            tv = q["v"] if isinstance(q["v"], str) else q["v"].get("segment","")
            slines = wrap(tc(tv), f_seg, LANE_W-30)
            return (qx+16, qx+16+max(tw(l, f_seg) for l in slines)+20, q["y"], q["y"]+30*len(slines))
        if k2 == "beat":
            bv = q["v"] if isinstance(q["v"], dict) else {"beat": q["v"]}
            txt2 = bv["beat"]+(f" ({bv['cite']})" if bv.get("cite") else "")
            blines = wrap(tc(txt2), f_beat, LANE_W-40)
            return (qx+16, qx+16+max(tw(l, f_beat) for l in blines), q["y"], q["y"]+20*len(blines)+6)
        if k2 == "laneborn":
            nb2 = q["v"]
            nlines = wrap(tc(nb2["chip"]), f_chip, LANE_W-40)
            hh = 30*len(nlines)
            if nb2.get("note"):
                hh += 24*len(wrap(tc(nb2["note"]), f_note, LANE_W-40)) + 8
            return (qx+16, qx+16+max(tw(l, f_chip) for l in nlines)+20, q["y"], q["y"]+hh)
        if k2 in ("arc", "mark"):
            return (qx-9, qx+9, q["y"]-9, q["y"]+9)
        return (qx-3, qx+3, q["y"], q["y"]+(q["h"] or 0))   # abandon tail

    # -------- fixed-point restack --------
    prev_key = None
    prev_splits = {}          # split id -> cy from the PREVIOUS pass (first pass: none)
    for iteration in range(8):
        lane_y = {lid: Y_TOP for lid in lane_ids}
        P = []
        split_pos = {}          # split id -> (lane, cx, cy) THIS pass
        arc_pos = {}            # arc id -> (lane, cx, cy) departure point
        mark_pos = {}           # arc id -> (lane, cx, cy) arrival point
        for lid in lane_ids:
            for it in raw[lid]:
                k = next(iter(it)); v = it[k]; cx = X[lid]
                if k == "join":
                    jid = v; j = g["joins"][jid]
                    yj = lane_y[lid] + 62
                    if j["from_split"] in split_pos:          # source placed this pass
                        yj = max(yj, split_pos[j["from_split"]][2] + JOIN_DROP)
                    elif j["from_split"] in prev_splits:      # fall back to prev pass pos
                        yj = max(yj, prev_splits[j["from_split"]][2] + JOIN_DROP)
                    # dodge ANY placed item whose box/text intersects the horizontal run
                    (slx, sxx, syy) = split_pos.get(j["from_split"], (lid, cx, yj-JOIN_DROP))
                    lo_x, hi_x = sorted((sxx, X[lid]))
                    def q_extent(q):
                        """logical (n-extent, t-extent) of a placed item — see q_extent_any"""
                        k2 = q["kind"]; qx, ql = q["cx"], q["w"]
                        if k2 in ("node", "stub", "ending"):
                            return (qx, qx+q["h"], q["y"], q["y"]+q["w"]) if horiz else (qx, qx+ql, q["y"], q["y"]+q["h"])
                        if k2 == "split":
                            sl2 = g["splits"][q["v"]]
                            return (qx-30, qx+44+tw(sl2["caption"].split("\n")[0], f_cap),
                                    q["y"]-30, q["y"]+30)
                        if k2 == "chip":
                            cv = q["v"] if isinstance(q["v"], dict) else {"chip": q["v"]}
                            return (qx+16, qx+36+tw(cv["chip"], f_chip), q["y"], q["y"]+34)
                        if k2 == "segment":
                            tv = q["v"] if isinstance(q["v"], str) else q["v"].get("segment","")
                            return (qx+16, qx+36+tw(tv, f_seg), q["y"], q["y"]+34)
                        if k2 == "beat":
                            bv = q["v"] if isinstance(q["v"], dict) else {"beat": q["v"]}
                            txt2 = bv["beat"]+(f" ({bv['cite']})" if bv.get("cite") else "")
                            return (qx+16, qx+16+tw(txt2, f_beat), q["y"], q["y"]+34)
                        if k2 == "laneborn":
                            return (qx+16, qx+16+min(560, LANE_W-40)+30, q["y"], q["y"]+96)
                        if k2 in ("arc", "mark"):
                            return (qx-9, qx+9, q["y"]-9, q["y"]+9)
                        return (qx-3, qx+3, q["y"], q["y"]+(q["h"] or 0))   # abandon tail
                    changed = True
                    while changed:
                        changed = False
                        for q in P:
                            if q["kind"] in ("join",): continue
                            x0q, x1q, y0q, y1q = q_extent(q)
                            if x1q < lo_x or x0q > hi_x: continue        # x doesn't overlap the run
                            if y0q-14 <= yj <= y1q+14:
                                yj = y1q + 24; changed = True
                    put_join = dict(kind="join", v=jid, lane=lid, cx=cx, y=yj, w=0, h=0)
                    P.append(put_join)
                    lane_y[lid] = max(lane_y[lid], yj) + SLOTS["join_after"]
                elif k == "node":
                    w,h = measure("node", v, lid)
                    nv = nodes[v] if isinstance(v, str) else v
                    P.append(dict(kind="node", v=nv, lane=lid, cx=cx, y=lane_y[lid], w=w, h=h))
                    lane_y[lid] += (w if horiz else h) + SLOTS["node_gap"]
                elif k == "beat":
                    # screen/certainty/traveller (#3-#5) are flat sibling keys on the item;
                    # carried through explicitly so existing cite/tone-dropping behavior
                    # (pre-existing, load-bearing for pixel-identical old renders) is untouched
                    extra = {ek: it[ek] for ek in ("screen", "certainty", "traveller") if ek in it}
                    bv = dict(v, **extra) if isinstance(v, dict) else (dict(beat=v, **extra) if extra else v)
                    P.append(dict(kind="beat", v=bv, lane=lid, cx=cx, y=lane_y[lid]+14, w=0, h=0))
                    lane_y[lid] += SLOTS["beat"]
                elif k == "segment":
                    P.append(dict(kind="segment", v=v, lane=lid, cx=cx, y=lane_y[lid]+8, w=0, h=0))
                    lane_y[lid] += SLOTS["segment"]
                elif k == "chip":
                    P.append(dict(kind="chip", v=v, lane=lid, cx=cx, y=lane_y[lid]+6, w=0, h=0))
                    lane_y[lid] += SLOTS["chip"]
                elif k == "split":
                    P.append(dict(kind="split", v=v, lane=lid, cx=cx, y=lane_y[lid]+round(50*B), w=0, h=0))
                    split_pos[v] = (lid, cx, lane_y[lid]+round(50*B))
                    lane_y[lid] += SLOTS["split"]
                elif k == "stub":
                    w,h = measure("stub", v, lid)
                    sv = stubs[v] if isinstance(v, str) else v
                    P.append(dict(kind="stub", v=sv, lane=lid, cx=min(cx+STUB_OFF, W-410), y=lane_y[lid], w=w, h=h, ref=v))
                    lane_y[lid] += max((w if horiz else h),70) + SLOTS["stub_gap"]
                elif k == "laneborn":
                    P.append(dict(kind="laneborn", v=v, lane=lid, cx=cx, y=lane_y[lid]+6, w=0, h=0))
                    lane_y[lid] += SLOTS["laneborn"]
                elif k == "arc":
                    P.append(dict(kind="arc", v=v, lane=lid, cx=cx, y=lane_y[lid]+14, w=0, h=0))
                    arc_pos[v] = (lid, cx, lane_y[lid]+14)
                    lane_y[lid] += SLOTS["arc"]
                elif k == "mark":
                    P.append(dict(kind="mark", v=v, lane=lid, cx=cx, y=lane_y[lid]+14, w=0, h=0))
                    mark_pos[v] = (lid, cx, lane_y[lid]+14)
                    lane_y[lid] += SLOTS["mark"]
                elif k == "abandon":
                    amt = max(60, min(int(v), 320))
                    P.append(dict(kind="abandon", v=amt, lane=lid, cx=cx, y=lane_y[lid], w=0, h=amt))
                    lane_y[lid] += amt + SLOTS["abandon_gap"]
                elif k == "ending":
                    w,h = measure("ending", v, lid)
                    P.append(dict(kind="ending", v=v, lane=lid, cx=max(40, cx-220), y=lane_y[lid], w=w, h=h))
                    lane_y[lid] += (w if horiz else h) + SLOTS["ending_gap"]
        prev_splits = dict(split_pos)   # carry into next pass for cross-lane anchoring
        key = tuple((p["kind"], p["lane"], p["y"]) for p in P)
        if key == prev_key: break
        prev_key = key
    else:
        raise RuntimeError("layout did not converge in 8 passes")

    y_bot = max(lane_y.values())      # logical t-extent of content
    n_bot = x0 + total                # logical n-extent actually used by the stacked lanes
    legend_h = 28*len(legend_lines) + 70
    # legend/footer sit below the content in SCREEN-Y, which is the t-axis in vertical
    # mode (content grows down) and the n-axis in horizontal mode (lanes stack down).
    # n_bot (not the raw W budget) is used for horizontal: W is sized to let LANE_W
    # grow toward 560px per lane, but with few lanes the lanes may occupy far less
    # than W, and W is no longer the screen dimension it is in vertical mode.
    content_screen_y = n_bot if horiz else y_bot
    content_screen_x = y_bot if horiz else W
    img_w = max(content_screen_x, 1400)
    img_h = max(content_screen_y + 60 + legend_h + 60, 1400)

    img = Image.new("RGB", (img_w,img_h), (246,246,244) if style=="tape" else (247,245,240))
    d = ImageDraw.Draw(img)

    INK=(25,28,34); GREY=(110,112,118); GREEN=(38,118,62); LANE=(150,148,142)
    YELLOW=(255,232,122); YE=(185,168,95); YTXT=(60,48,8)
    CH=(43,87,151); CHDIM=(120,120,126); SEGF=(70,110,60)
    DEADF=(243,234,234); DEADE=(150,74,74); GREENF=(236,246,238); GREENT=(16,70,38)
    if style=="tape": INK=(20,20,22); GREEN=(15,15,17); LANE=(70,70,74); DEADE=(140,30,30)

    # epistemic colour (#4): classic/weight render full colour; dash/tape carry a letter glyph instead
    CERTAINTY_COLOR = {"seen": GREY, "flashback": CH, "seen-later": GREEN, "never-shown": (150,44,44)}
    CERTAINTY_GLYPH = {"seen": "S", "flashback": "F", "seen-later": "L", "never-shown": "N"}

    # ---- node-type palette (per-film override via meta.node_types) ----
    nt = {"thread": {"color": GREEN, "weight": 10},
          "lane":   {"color": LANE,  "weight": 4},
          "pre":    {"color": LANE,  "weight": 4},
          "abandon":{"color": LANE,  "weight": 3},
          "death":  {"color": DEADE, "weight": 3},
          "join":   {"color": GREEN, "weight": 10}}
    _ov = g.get("meta", {}).get("node_types") or {}
    def _lighten(c, f=0.62): return tuple(int(v + (255-v)*f) for v in c)
    def _darken(c, f=0.42):  return tuple(int(v*f) for v in c)
    D_EDGE, D_FILL, D_TEXT = DEADE, DEADF, (90,20,20)
    if isinstance(_ov.get("death"), dict) and "color" in _ov["death"]:
        D_EDGE = tuple(_ov["death"]["color"]); D_FILL = _lighten(D_EDGE); D_TEXT = _darken(D_EDGE)
    E_EDGE, E_FILL, E_TEXT = GREEN, GREENF, GREENT
    if isinstance(_ov.get("ending"), dict) and "color" in _ov["ending"]:
        E_EDGE = tuple(_ov["ending"]["color"]); E_FILL = _lighten(E_EDGE); E_TEXT = _darken(E_EDGE)
    S_FILL, S_EDGE, S_TEXT = YELLOW, YE, YTXT
    if isinstance(_ov.get("split"), dict):
        _so = _ov["split"]
        S_FILL = tuple(_so.get("color", YELLOW)); S_EDGE = tuple(_so.get("edge", YE)); S_TEXT = tuple(_so.get("text", YTXT))
    LOOPC = LANE
    if isinstance(_ov.get("loop"), dict) and "color" in _ov["loop"]:
        LOOPC = tuple(_ov["loop"]["color"])
    _WSTYLE = {"classic": {},
               "weight": {"thread": 11, "lane": 6, "pre": 6, "death": 2, "join": 11},
               "dash":   {"thread": 7,  "lane": 5, "pre": 5, "death": 4, "join": 7},
               "tape":   {"thread": 10, "lane": 8, "pre": 8, "abandon": 5, "death": 8, "join": 10}}
    for _k, _v in _WSTYLE.get(style, {}).items():
        nt[_k]["weight"] = _v
    for _k in ("thread", "lane", "pre", "abandon", "join"):   # per-film colour/weight overrides
        if isinstance(_ov.get(_k), dict):
            if "color" in _ov[_k]: nt[_k]["color"] = tuple(_ov[_k]["color"])
            if "weight" in _ov[_k]: nt[_k]["weight"] = int(_ov[_k]["weight"])

    def stroke(pts, color, width, st="solid", dash=22):
        if st=="solid":
            for i in range(len(pts)-1): d.line((*pts[i],*pts[i+1]), fill=color, width=width)
            return
        for i in range(len(pts)-1):
            x1,y1=pts[i]; x2,y2=pts[i+1]; seg=math.hypot(x2-x1,y2-y1)
            if seg==0: continue
            nn=max(int(round(seg/dash)),1)
            cell=1.0/nn
            for kk in range(nn):
                t0=kk*cell; t1=min(t0+cell*(0.55 if st=="dash" else 0.35),1)
                d.line((x1+(x2-x1)*t0, y1+(y2-y1)*t0, x1+(x2-x1)*t1, y1+(y2-y1)*t1), fill=color, width=width)
    def elbow45(pts):
        out=[pts[0]]
        for i in range(1,len(pts)):
            xa,ya=out[-1]; xb,yb=pts[i]; dx,dy=xb-xa,yb-ya
            if dx==0 or dy==0 or abs(dx)==abs(dy): out.append((xb,yb)); continue
            adx,ady=abs(dx),abs(dy)
            if adx>ady:
                m=(xa+(adx-ady)*(1 if dx>0 else -1), ya); out+=[m,(m[0]+ady*(1 if dx>0 else -1), yb)]
            else:
                m=(xa, ya+(ady-adx)*(1 if dy>0 else -1)); out+=[m,(xb, m[1])]
        return out
    def cap_x(pt, color, s=15):
        x2,y2=pt
        d.line((x2-s,y2-s,x2+s,y2+s), fill=color, width=4)
        d.line((x2-s,y2+s,x2+s,y2-s), fill=color, width=4)
    def head(pt, prev, color, size=15):
        (x2,y2),(x1,y1)=pt,prev
        ang=math.atan2(y2-y1,x2-x1)
        for da in (0.45,-0.45):
            d.line((x2,y2,x2-size*math.cos(ang+da),y2-size*math.sin(ang+da)), fill=color, width=4)

    def w_of(kind):
        return nt[kind]["weight"]
    def s_of(kind):
        if style!="dash": return "solid"
        return {"thread":"solid","lane":"solid","pre":"dash","abandon":"dot","death":"dash","join":"solid"}[kind]
    def col_of(kind):
        return nt[kind]["color"]

    def seg(pts, kind):
        """pts are logical (n,t) pairs; single transpose at draw time (brief pass2b #1)."""
        pts = [XY(t, n) for (n, t) in pts]
        pts = elbow45(pts) if style=="tape" else pts
        stroke(pts, col_of(kind), w_of(kind), s_of(kind))
        if kind=="death":
            if style in ("weight","dash"): cap_x(pts[-1], col_of("death"))
            elif style=="tape":
                s=w_of(kind)*0.9
                x2,y2=pts[-1]; d.rectangle((x2-s/2,y2-s/2,x2+s/2,y2+s/2), fill=col_of("death"))
            else: head(pts[-1], pts[-2], col_of("death"))
        elif kind in ("thread","join") and style!="tape":
            head(pts[-1], pts[-2], col_of(kind))

    # ---------- chrome ----------
    m = g["meta"]
    f_title=F(54,bold=True); f_sub=F(22); f_route=F(20,bold=True); f_foot=F(16); f_big=F(28,bold=True)
    d.text((40,24), tc(m["title"]), font=f_title, fill=INK)
    d.text((40,94), tc(m["subtitle"]), font=f_sub, fill=GREY)
    d.text((40,128), tc(m["thread_label"]), font=f_route, fill=nt["thread"]["color"])
    d.line((40,164,img_w-40,164), fill=INK, width=3)

    by_lane = {lid: sorted([p for p in P if p["lane"]==lid], key=lambda p: p["y"]) for lid in lane_ids}
    splits_pos = {p["v"]: (p["lane"], p["cx"], p["y"]) for p in P if p["kind"]=="split"}
    joins_by_split = {}
    for jid, j in g.get("joins", {}).items():
        joins_by_split.setdefault(j["from_split"], []).append(jid)

    # ---------- lane base lines ----------
    for lid in lane_ids:
        its = by_lane[lid]
        born = next((p for p in its if p["kind"]=="laneborn"), None)
        if born and born["v"].get("from_split"):
            sp = born["v"]["from_split"]
            (sl, sx, sy) = splits_pos[sp]
            y_start = born["y"]+30
            seg([(sx-21, sy+21), (X[lid], y_start)], "lane")
            seg([(X[lid], y_start), (X[lid], y_bot)], "lane")
        else:
            seg([(X[lid], Y_TOP), (X[lid], y_bot)], "pre")

    # ---------- thread verticals (carried through EVERY item kind) ----------
    for lid in lane_ids:
        its = by_lane[lid]
        in_joins = sorted([p["y"] for p in its if p["kind"]=="join"])
        born = next((p for p in its if p["kind"]=="laneborn"), None)
        if in_joins:
            carry_from = in_joins[0]           # green starts at the first join dot
        elif born is None:
            carry_from = Y_TOP                 # the opening lane: thread from the very top
        else:
            carry_from = None                  # born lane, never joined: no green
        for p in its:
            kind = p["kind"]
            if kind == "join":
                jid = p["v"]; j = g["joins"][jid]
                yj = p["y"]
                (sl, sx, sy) = splits_pos[j["from_split"]]
                if joins_by_split[j["from_split"]][0] == jid:
                    seg([(sx, sy+34), (sx, yj)], "thread")     # down the source lane
                seg([(sx, yj), (X[lid], yj)], "thread")        # across to target
                carry_from = yj
            elif kind == "split":
                if carry_from is not None:
                    seg([(X[lid], carry_from), (X[lid], p["y"]-34)], "thread")
                carry_from = None if p["v"] in joins_by_split else p["y"]+34
            elif kind in ("node","beat","chip","segment","laneborn","ending","stub"):
                if carry_from is not None:
                    bottom = p["y"] + (p["h"] or 34)
                    if bottom > carry_from:            # thread only flows DOWN — never up into pre-history
                        seg([(X[lid], carry_from), (X[lid], bottom)], "thread")
                        carry_from = bottom
            elif kind == "abandon":
                # world runs on: tail renders regardless of carry state
                seg([(X[lid], p["y"]), (X[lid], p["y"]+p["h"])], "abandon")
                if carry_from is not None:
                    seg([(X[lid], carry_from), (X[lid], p["y"])], "thread")
                carry_from = None
            elif kind == "arc":
                # traveller departs: thread stops here (resumes at the mark)
                a_def = g.get("arcs", {}).get(v, {})
                if carry_from is not None and a_def.get("carry_through", True):
                    seg([(X[lid], carry_from), (X[lid], p["y"])], "thread")
                    carry_from = None
                elif not a_def.get("carry_through", True):
                    pass                        # another traveller's arc: thread ignores it
                else:
                    carry_from = None
            elif kind == "mark":
                # traveller arrives: thread resumes at the dot
                a_def = g.get("arcs", {}).get(v, {})
                if a_def.get("arrive_thread", True):
                    carry_from = p["y"]
                # else: someone else's arrival — our thread is unaffected
        if carry_from is not None:
            last_bottom = Y_TOP
            for p in its:
                b = p["y"] + (p["h"] or 34)
                if b > last_bottom: last_bottom = b
            if last_bottom > carry_from:
                seg([(X[lid], carry_from), (X[lid], last_bottom)], "thread")

    # ---------- stubs diagonals ----------
    for lid in lane_ids:
        for p in by_lane[lid]:
            if p["kind"]=="stub":
                prev_split = None
                for q in by_lane[lid]:
                    if q["kind"]=="split" and q["y"] < p["y"]: prev_split = q
                if prev_split:
                    seg([(prev_split["cx"]+22, prev_split["y"]+22), (p["cx"]-8, p["y"]+40)], "death")

    # screen-space boxes already claimed by drawn content — arc staples/bulges
    # register themselves here so beat/label placement in horizontal mode
    # (where a lane's whole row is one thin band) can avoid drawing text on
    # top of them, the same "try a spot, check, push" idea as _label_clear.
    occupied = []
    def _place_perp(lx, sy, box_w, box_h):
        """Choose a screen-Y for a label block that clears the row's thread
        line and anything already in `occupied` — horizontal mode's answer to
        vertical mode's fixed 'sy-10' (text can't sit ON a horizontal line the
        way it can sit beside a vertical one)."""
        if not horiz:
            return sy - 10
        PERP = 18
        for k in range(6):
            for cand in (sy - PERP - box_h - k*(box_h+8), sy + PERP + k*(box_h+8)):
                box = (lx-4, cand-4, lx+box_w+4, cand+box_h+4)
                if not any(not (box[2]<o[0] or box[0]>o[2] or box[3]<o[1] or box[1]>o[3]) for o in occupied):
                    occupied.append(box)
                    return cand
        cand = sy + PERP
        occupied.append((lx-4, cand-4, lx+box_w+4, cand+box_h+4))
        return cand

    # ---------- time-travel arcs (travel / return / loop) ----------
    def _hseg_dodge(y, x_lo, x_hi, exclude=()):
        """push a horizontal run down until it clears placed items"""
        for _ in range(6):
            hit = None
            for q in P:
                if q["kind"] in ("join","arc","mark") or q["lane"] in exclude: continue
                qx0, qx1, qy0, qy1 = q_extent_any(q)
                if qx1 < x_lo or qx0 > x_hi: continue
                if qy0-14 <= y <= qy1+14:
                    hit = qy1 + 24
            if hit is None: break
            y = hit
        return y

    # version counters (#5): ordinal count of a traveller's arc departures, in arc_pos order
    traveller_seen, arc_ordinal = {}, {}
    for aid_ in arc_pos:
        tvl = g["arcs"][aid_].get("traveller")
        if tvl:
            traveller_seen[tvl] = traveller_seen.get(tvl, 0) + 1
            arc_ordinal[aid_] = traveller_seen[tvl]
    versioning = g.get("meta", {}).get("versioning")

    for aid, a in g.get("arcs", {}).items():
        if aid not in arc_pos or aid not in mark_pos: continue
        (fl, fx, fy) = arc_pos[aid]
        (tl, tx, ty) = mark_pos[aid]
        kind = a.get("kind", "travel")
        acol = tuple(a["color"]) if "color" in a else (
               nt["thread"]["color"] if kind == "travel" else (
               LOOPC if kind == "loop" else GREY))
        awd  = 7 if kind != "loop" else 5
        label = tc(a.get("label", ""))
        if versioning == "crossing-count" and a.get("traveller"):
            suffix = f"{a['traveller']}({arc_ordinal.get(aid, 1)})"
            label = f"{label} — {suffix}" if label else suffix
        lw_ = tw(label, f_cap)

        def _label_clear(lx, ly, extra_h=14):
            """push a label up/down until its box hits nothing.
            extra_h: label-box height below ly. Interval labels draw a second
            line (duration) at ly+22, so they pass 42; elbow arcs keep the
            historical 14 so existing charts stay pixel-identical."""
            for _ in range(12):
                box = (lx-4, lx+lw_+4, ly-8, ly+extra_h)
                hit = False
                for q in P:
                    if q["kind"] in ("join","arc","mark"): continue
                    qx0, qx1, qy0, qy1 = q_extent_any(q)
                    if not (qx1 < box[0] or qx0 > box[1] or qy1 < box[2] or qy0 > box[3]):
                        hit = True; break
                if not hit: return ly
                ly += 22
            return ly

        # fx,fy,tx,ty (and everything derived below: bx,ox,top_y,fy2,ty2,lx,ly) are all
        # logical (n or t) values, exactly like the layout core. XY() is applied only
        # at the point each point actually reaches a PIL draw call — the same single-
        # transpose-at-draw-time discipline as seg()/stroke().
        def dot(nn, tt, r, fill, outline, ow):
            x, y = XY(tt, nn)
            d.ellipse((x-r,y-r,x+r,y+r), fill=fill, outline=outline, width=ow)
        def dtext(nn, tt, txt, font, fill):
            d.text(XY(tt, nn), txt, font=font, fill=fill)

        if "interval" in a:
            # loop-rectangle (#2): enter at depart, box height ~ duration, re-emerge earlier
            depart, arrive = a["interval"]
            duration = abs(depart - arrive)
            unit = g.get("meta", {}).get("timescale", {}).get("unit", "")
            dur_label = f"{duration:g} {unit}".strip()
            box_h = max(50, min(360, round(duration * PX_PER_UNIT)))
            side = a.get("side") or ("left" if tx <= fx else "right")
            sgn = 1 if side == "right" else -1
            bx = fx + sgn*180 if tl == fl else (min(fx,tx)-56 if side == "left" else max(fx,tx)+56)
            top_y = fy - box_h
            d.line((*XY(fy,fx), *XY(fy,bx)), fill=acol, width=awd)
            d.line((*XY(fy,bx), *XY(top_y,bx)), fill=acol, width=awd)
            d.line((*XY(top_y,bx), *XY(top_y,fx)), fill=acol, width=awd)
            if horiz:
                corners = [XY(fy,fx), XY(fy,bx), XY(top_y,bx), XY(top_y,fx)]
                xs = [c[0] for c in corners]; ys = [c[1] for c in corners]
                occupied.append((min(xs),min(ys),max(xs),max(ys)))
                # horizontal interval label: screen-space, two lines stacked
                # DOWN-SCREEN (the across axis) just below the staple. The
                # vertical (t,n) dtext transpose would put a "+22 second line"
                # to the RIGHT (overprinting the label), so horizontal places
                # both lines explicitly in screen coords and registers the box.
                sx0 = min(xs) + 24
                sy0 = max(ys) + 14
                for _ in range(8):
                    lbox = (sx0-4, sy0-4, sx0+lw_+4, sy0+48)
                    if not any(not (lbox[2]<o[0] or lbox[0]>o[2] or lbox[3]<o[1] or lbox[1]>o[3])
                               for o in occupied):
                        break
                    sy0 += 18
                occupied.append((sx0-4, sy0-4, sx0+lw_+4, sy0+48))
            if fx != tx or abs(top_y - ty) > 2:
                conn = [XY(top_y,fx), XY(ty,tx)]
                conn = elbow45(conn) if style=="tape" else conn
                stroke(conn, acol, awd)
                head(conn[-1], conn[-2], acol)
            else:
                head(XY(top_y,fx), XY(top_y,bx), acol)
            dot(fx, fy, 9, (255,255,255), acol, 4)
            dot(tx, ty, 7, acol, (255,255,255), 3)
            if horiz:
                d.text((sx0, sy0), label, font=f_cap, fill=acol if kind!="loop" else GREY)
                d.text((sx0, sy0+22), dur_label, font=f_cite, fill=GREY)
            else:
                lx = bx + sgn*16 if side == "right" else bx - 16 - lw_
                ly = _label_clear(lx, (fy+top_y)/2 - 8, extra_h=42)
                dtext(lx, ly, label, f_cap, acol if kind!="loop" else GREY)
                dtext(lx, ly+22, dur_label, f_cite, GREY)
        elif tl == fl:
            # self-lane loop: bulge sideways
            side = a.get("side") or "right"
            if side == "left" and fx - 220 < 10: side = "right"   # don't bulge off-canvas
            sgn = 1 if side == "right" else -1
            bx = fx + sgn*180
            for _ in range(6):   # push bulge clear of every item box it would cross
                clash = False
                for q in P:
                    if q["kind"] in ("join","arc","mark"): continue
                    qx0, qx1, qy0, qy1 = q_extent_any(q)
                    if not (qx1 < min(fx,bx)-6 or qx0 > max(fx,bx)+6 or
                            qy1 < min(fy,ty)-8 or qy0 > max(fy,ty)+8):
                        clash = True; break
                if not clash: break
                bx += sgn*34
            fy2 = _hseg_dodge(fy, min(fx,bx), max(fx,bx))
            ty2 = _hseg_dodge(ty, min(tx,bx), max(tx,bx))
            pts = [XY(t_,n_) for (n_,t_) in [(fx, fy), (fx, fy2), (bx, fy2), (bx, ty2), (tx, ty2)]]
            stroke(pts, acol, awd)
            head(pts[-1], pts[-2], acol)
            if horiz:
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                occupied.append((min(xs),min(ys),max(xs),max(ys)))
            dot(fx, fy, 9, (255,255,255), acol, 4)
            dot(tx, ty, 7, acol, (255,255,255), 3)
            lx = bx + sgn*16 if side == "right" else bx - 16 - lw_
            ly = _label_clear(lx, (fy2+ty2)/2 - 8)
            dtext(lx, ly, label, f_cap, acol if kind!="loop" else GREY)
        else:
            # cross-lane: out vertical, across, in
            side = a.get("side") or ("left" if tx < fx else "right")
            sgn = -1 if side == "left" else 1
            ox = min(fx,tx) - 56 if side == "left" else max(fx,tx) + 56
            for _ in range(4):   # vertical corridor: push outward past items
                clash = False
                for q in P:
                    if q["kind"] in ("join","arc","mark"): continue
                    qx0, qx1, qy0, qy1 = q_extent_any(q)
                    if qx0-6 <= ox <= qx1+6 and not (qy1 < min(fy,ty) or qy0 > max(fy,ty)):
                        clash = True
                if not clash: break
                ox += sgn*34
            fy2 = _hseg_dodge(fy, min(fx,ox), max(fx,ox))
            ty2 = _hseg_dodge(ty, min(tx,ox), max(tx,ox))
            pts = [XY(t_,n_) for (n_,t_) in [(fx, fy), (fx, fy2), (ox, fy2), (ox, ty2), (tx, ty2)]]
            stroke(pts, acol, awd)
            head(pts[-1], pts[-2], acol)
            if horiz:
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                occupied.append((min(xs),min(ys),max(xs),max(ys)))
            dot(fx, fy, 9, (255,255,255), acol, 4)
            dot(tx, ty, 7, acol, (255,255,255), 3)
            lx = ox + 16 if side == "right" else ox - 16 - lw_
            ly = _label_clear(lx, (fy2+ty2)/2 - 8)
            dtext(lx, ly, label, f_cap, acol if kind!="loop" else GREY)

    # ---------- markers / boxes / text ----------
    # Every item's (cx=n, y=t) anchor is transposed to screen (sx,sy) right here — the
    # single draw-time transpose (brief pass2b #1). Text-bearing boxes then render
    # LITERALLY at (sx,sy,sx+w,sy+h): text can't rotate, so w/h (screen width/height)
    # never swap here, only the anchor moves — the axis-conditional lives upstream in
    # q_extent()/q_extent_any() and the node/stub/ending cursor-advance, not in this loop.
    for p in P:
        kind, v, lid, cx, y, w, h = p["kind"], p["v"], p["lane"], p["cx"], p["y"], p["w"], p["h"]
        sx, sy = XY(y, cx)
        if kind=="node":
            lines = wrap(v["body"], f_body, w-30)
            d.rounded_rectangle((sx,sy,sx+w,sy+h), radius=12, fill=(255,255,255), outline=INK, width=3)
            d.text((sx+15,sy+10), tc(v["title"]), font=f_node, fill=INK)
            yy=sy+40
            for t in lines: d.text((sx+15,yy), t, font=f_body, fill=INK); yy+=22
            if v.get("cite"): d.text((sx+15,yy+2), v["cite"], font=f_cite, fill=GREY)
        elif kind=="stub":
            lines = wrap(v.get("sub",""), f_body, w-30)
            d.rounded_rectangle((sx,sy,sx+w,sy+h), radius=10, fill=D_FILL, outline=D_EDGE, width=3)
            d.text((sx+15,sy+10), tc(v["title"]), font=f_node, fill=D_TEXT)
            yy=sy+40
            for t in lines: d.text((sx+15,yy), t, font=f_body, fill=D_TEXT); yy+=22
        elif kind=="ending":
            lines = wrap(v["body"], f_body, w-30)
            uncertain = v.get("uncertain")
            fill_c = (238,238,234) if uncertain else E_FILL
            edge_c = GREY if uncertain else E_EDGE
            text_c = GREY if uncertain else E_TEXT
            d.rounded_rectangle((sx,sy,sx+w,sy+h), radius=12, fill=fill_c,
                                outline=edge_c, width=(1 if uncertain else 3))
            if uncertain:
                stroke([(sx,sy),(sx+w,sy),(sx+w,sy+h),(sx,sy+h),(sx,sy)], edge_c, 3, "dash")
                d.text((sx+w-46,sy+8), "?", font=F(34,bold=True), fill=edge_c)
            d.text((sx+15,sy+10), tc(v["title"]), font=f_node, fill=text_c)
            yy=sy+40
            for t in lines: d.text((sx+15,yy), t, font=f_body, fill=text_c); yy+=22
            if v.get("cite"): d.text((sx+15,yy+2), v["cite"], font=f_cite, fill=GREY)
        elif kind=="split":
            sl = g["splits"][v]
            r=30
            d.ellipse((sx-r,sy-r,sx+r,sy+r), fill=S_FILL, outline=S_EDGE, width=4)
            letter=sl["letter"]
            d.text((sx-tw(letter,f_big)/2, sy-18), letter, font=f_big, fill=S_TEXT)
            cap_lines = []
            for part in sl["caption"].split("\n"):
                cap_lines += wrap(tc(part), f_cap, max(200, img_w-80-(sx+44)))
            for i,cl in enumerate(cap_lines):
                d.text((sx+44, sy-12+i*24), cl, font=f_cap, fill=GREY)
        elif kind=="join":
            j = g["joins"][v]
            d.ellipse((sx-13, sy-13, sx+13, sy+13), fill=nt["join"]["color"], outline=(255,255,255), width=3)
            side = j.get("side","right")
            lw = tw(j["label"], f_cap)
            lbl = tc(j["label"])
            lw = tw(lbl, f_cap)
            if side=="left" and sx-18-lw < 8: side = "right"   # auto-flip: don't clip at edge
            if side=="left": d.text((sx-18-lw, sy-30), lbl, font=f_cap, fill=nt["join"]["color"])
            else: d.text((sx+18, sy-30), lbl, font=f_cap, fill=nt["join"]["color"])
        elif kind=="beat":
            if isinstance(v,str): v={"beat":v}
            tone=v.get("tone"); col=GREY
            if tone=="death": col=(150,44,44)
            elif tone=="good": col=GREEN
            certainty = v.get("certainty")
            if certainty and style in ("classic","weight"):
                col = CERTAINTY_COLOR[certainty]
            side=v.get("side","right")
            d.ellipse((sx-5,sy-5,sx+5,sy+5), fill=col)
            txt=v["beat"]+(f" ({v['cite']})" if v.get("cite") else "")
            txt = tc(txt)
            blines = wrap(txt, f_beat, LANE_W-40)
            # label_w/h + lx0 approximate the full label footprint (text plus room
            # for a trailing certainty glyph/screen chip) so _place_perp's collision
            # check doesn't undersize the box it's clearing.
            label_w = max((tw(bl,f_beat) for bl in blines), default=0)
            label_h = 20*len(blines)+6
            lx0 = sx+16 if side=="right" else sx-16-label_w-60
            ly0 = _place_perp(lx0, sy, label_w+60, label_h)
            for i,bline in enumerate(blines):
                if side=="right": d.text((sx+16, ly0+i*20), bline, font=f_beat, fill=col)
                else: d.text((sx-16-tw(bline,f_beat), ly0+i*20), bline, font=f_beat, fill=col)
            tail_w = max((tw(bl,f_beat) for bl in blines), default=0)
            tail_x = sx+16+tail_w if side=="right" else sx-16-tail_w
            if certainty and style in ("dash","tape"):
                gx = tail_x+10 if side=="right" else tail_x-20
                d.text((gx, ly0), CERTAINTY_GLYPH[certainty], font=f_cite, fill=GREY)
                tail_x = gx + (16 if side=="right" else -4)
            if v.get("screen"):
                chip_lbl = v["screen"].upper()
                chip_w = tw(chip_lbl, f_cite)+10
                chx = tail_x+8 if side=="right" else tail_x-chip_w-8
                d.rounded_rectangle((chx, ly0+1, chx+chip_w, ly0+19), radius=4, fill=YELLOW, outline=YE, width=1)
                d.text((chx+5, ly0+2), chip_lbl, font=f_cite, fill=YTXT)
        elif kind=="chip":
            if isinstance(v,str): v={"chip":v}
            fill=CHDIM if v.get("dim") else CH
            chip_txt = tc(v["chip"])
            clines = wrap(chip_txt, f_chip, LANE_W-30)
            wid=int(max(tw(l,f_chip) for l in clines))+20
            d.rounded_rectangle((sx+16,sy,sx+16+wid,sy+30*len(clines)), radius=6, fill=fill)
            for i,cline in enumerate(clines):
                d.text((sx+26,sy+4+i*30), cline, font=f_chip, fill=(255,255,255))
        elif kind=="segment":
            txt=v if isinstance(v,str) else v.get("segment","")
            txt = tc(txt)
            slines2 = wrap(txt, f_seg, LANE_W-30)
            wid=int(max(tw(l,f_seg) for l in slines2))+20
            d.rounded_rectangle((sx+16,sy,sx+16+wid,sy+30*len(slines2)), radius=6, fill=SEGF)
            for i,sline in enumerate(slines2):
                d.text((sx+26,sy+5+i*30), sline, font=f_seg, fill=(255,255,255))
        elif kind=="laneborn":
            nb=v
            chip_txt = tc(nb["chip"])
            nlines = wrap(chip_txt, f_chip, LANE_W-40)
            wid=int(max(tw(l,f_chip) for l in nlines))+20
            d.rounded_rectangle((sx+16,sy,sx+16+wid,sy+30*len(nlines)), radius=6, fill=CHDIM)
            for i,nline in enumerate(nlines):
                d.text((sx+26,sy+4+i*30), nline, font=f_chip, fill=(255,255,255))
            if nb.get("note"):
                ny = sy + 30*len(nlines) + 8
                for i,t in enumerate(wrap(tc(nb["note"]), f_note, LANE_W-40)):
                    d.text((sx+16, ny+i*24), t, font=f_note, fill=GREY)

    # ---------- legend follows content ----------
    ry = content_screen_y + 60
    d.rounded_rectangle((40, ry, img_w-40, ry+28*len(legend_lines)+70), radius=10,
                        fill=(255,255,255), outline=INK, width=2)
    d.text((60, ry+12), "The Index / How to Read", font=F(20,bold=True), fill=INK)
    yy=ry+48
    for l in legend_lines:
        d.text((60,yy), tc(l), font=f_note, fill=INK); yy+=28
    d.text((40, ry+28*len(legend_lines)+82), tc(m["footer"]), font=f_foot, fill=GREY)

    # optional hitboxes (GUI mode): screen-space rects of the placed story items
    if hitboxes is not None:
        for p in P:
            k, cx, y = p["kind"], p["cx"], p["y"]
            w, h = p.get("w") or 0, p.get("h") or 0
            ref = p.get("v")
            if k == "node":      box, rid, rlabel = (cx, y, cx+w, y+h), ref.get("id",""), ref.get("title","")
            elif k == "stub":    box, rid, rlabel = (cx, y, cx+w, y+h), p.get("ref",""), (ref or {}).get("title","")
            elif k == "ending":  box, rid, rlabel = (cx, y, cx+w, y+h), "ENDING", (ref or {}).get("title","")
            elif k == "split":   r = 30; box, rid, rlabel = (cx-r, y-r, cx+r, y+r), str(ref), (g["splits"][ref]["caption"].split("\n")[0])
            elif k == "join":    box, rid, rlabel = (cx-16, y-16, cx+16, y+16), str(ref), (g["joins"][ref].get("label") or ref)
            elif k == "arc":     box, rid, rlabel = (cx-12, y-12, cx+12, y+12), "arc:"+str(ref), g["arcs"][ref].get("label") or ref
            elif k == "mark":    box, rid, rlabel = (cx-10, y-10, cx+10, y+10), "mark:"+str(ref), g["arcs"][ref].get("label") or ref
            else: continue
            x0b, y0b, x1b, y1b = box
            sx0, sy0 = (x0b, y0b) if horiz else (y0b, x0b)
            sx1, sy1 = (x1b, y1b) if horiz else (y1b, x1b)
            hitboxes.append({"kind": k, "id": rid, "label": rlabel,
                             "lane": p.get("lane"), "rect": [sx0, sy0, sx1, sy1]})

    return img

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("graph"); ap.add_argument("-o","--out",default=None)
    ap.add_argument("--style", default="classic", choices=["classic","weight","dash","tape"])
    ap.add_argument("--density", default="normal", choices=["compact","normal"])
    ap.add_argument("--print-hitboxes", action="store_true")
    ap.add_argument("--orientation", default="vertical", choices=["vertical","horizontal"])
    a = ap.parse_args()
    g = json.load(open(a.graph))
    errs = validate(g)
    if errs:
        print("VALIDATION FAILED — fix the JSON (story), not the engine:")
        for e in errs: print("  -", e)
        sys.exit(2)
    out = a.out or a.graph.replace(".json", f"-{a.style}.png")
    hit = [] if a.print_hitboxes else None
    img = build(g, a.style, density=a.density, orientation=a.orientation, hitboxes=hit)
    if hit is not None:
        print(json.dumps(hit, indent=1))
    img.save(out, "PNG")
    print("saved", out, img.size)
