#!/usr/bin/env python3
"""Track the ZSA Voyager (Oryx) layout that this ZMK keymap is ported from.

The Voyager is the daily driver; the Kibard keymap is a hand-port of it. This
fetches the live layout from Oryx, folds the Voyager's 52 keys down onto the
Kibard's 34 positions, and diffs that against the snapshot recorded the last
time the two were in sync -- so porting a change is a matter of reading the
diff instead of remembering what you edited.

    tools/sync-oryx.py            # what changed in Oryx since the last sync
    tools/sync-oryx.py show 2     # the Oryx layer, drawn in Kibard geometry
    tools/sync-oryx.py snapshot   # mark as ported (run after editing the keymap)
    tools/sync-oryx.py compare    # Oryx vs the checked-in ZMK keymap

Exit status of the default `diff` is 1 when there are unported changes, so it
works in a hook or CI. Stdlib only, no auth needed -- Oryx layouts are public.
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT = REPO / "tools" / "oryx-snapshot.json"

ORYX_API = "https://oryx.zsa.io/graphql"
LAYOUT_ID = os.environ.get("ORYX_LAYOUT_ID", "6ye0X")

QUERY = """
query($hashId: String!, $revisionId: String!) {
  layout(hashId: $hashId, revisionId: $revisionId) {
    hashId
    revision { hashId title model qmkVersion layers { position title keys } }
  }
}
"""

# Voyager key index -> Kibard key position. The Voyager is 6x4 + 2 thumbs per
# half, flat left-then-right; the Kibard uses its inner 5 columns of rows 1-3
# plus both thumb pairs. Left half is Voyager 0-25, right half 26-51.
#
#   Voyager left            Voyager right
#   [ 0 .. 5]  row 0        [26 ..31]     <- unused (Voyager number row)
#   [ 6 ..11]  row 1        [32 ..37]
#   [12 ..17]  row 2        [38 ..43]
#   [18 ..23]  row 3        [44 ..49]
#   [24 25]    thumbs       [50 51]
POSITION_MAP = [
    7, 8, 9, 10, 11,        32, 33, 34, 35, 36,   # Kibard row 0  (pos 0-9)
    13, 14, 15, 16, 17,     38, 39, 40, 41, 42,   # Kibard row 1  (pos 10-19)
    19, 20, 21, 22, 23,     44, 45, 46, 47, 48,   # Kibard row 2  (pos 20-29)
    24, 25,                 50, 51,               # thumbs        (pos 30-33)
]

# Oryx layer position -> (expected Oryx title, ZMK layer index or None, ZMK name).
# None means the layer has no Kibard counterpart and is skipped. The titles are
# asserted on every run: if you rename or reorder layers in Oryx the tool stops
# rather than silently diffing the wrong pair.
LAYER_MAP = [
    ("Graphish", 0, "Graphmod"),
    ("Symbols",  1, "Symbols"),
    ("Numpad",   2, "Numpad"),
    ("Right",    3, "Right"),
    ("Mouse",    6, "Mouse"),
    ("Vim",      5, "Vim"),
    ("Navigate", 4, "Navigate"),
    ("Function", 7, "Functions"),
    ("Hex",      9, "Hex"),
]

# ---------------------------------------------------------------- keycodes ---

# QMK/Oryx keycode -> ZMK keycode. The SE_* names resolve to the #defines at
# the top of config/kibard.keymap.
KEYCODES = {
    "KC_NO": None, "KC_TRANSPARENT": None,
    "KC_BSPC": "BSPC", "KC_DELETE": "DEL", "KC_ENTER": "RET", "KC_SPACE": "SPACE",
    "KC_TAB": "TAB", "KC_INSERT": "INS", "KC_CAPS": "CAPS", "KC_PSCR": "PRINTSCREEN",
    "KC_LEFT": "LEFT", "KC_RIGHT": "RIGHT", "KC_UP": "UP", "KC_DOWN": "DOWN",
    "KC_HOME": "HOME", "KC_END": "END", "KC_PAGE_UP": "PG_UP", "KC_PGDN": "PG_DN",
    "KC_LEFT_SHIFT": "LSHIFT", "KC_LEFT_CTRL": "LCTRL", "KC_LEFT_ALT": "LALT",
    "KC_LEFT_GUI": "LGUI", "KC_RIGHT_SHIFT": "RSHIFT", "KC_RIGHT_CTRL": "RCTRL",
    "KC_RIGHT_ALT": "RALT", "KC_RIGHT_GUI": "RGUI",
    "KC_COMMA": "COMMA", "KC_DOT": "DOT",
    "KC_EXLM": "SE_EXCLAM", "KC_PERC": "SE_PERCENT", "KC_HASH": "SE_POUND",
    "KC_AUDIO_VOL_UP": "K_VOL_UP", "KC_AUDIO_VOL_DOWN": "K_VOL_DN",
    "KC_AUDIO_MUTE": "K_MUTE", "KC_MEDIA_PLAY_PAUSE": "K_PP",
    "KC_MEDIA_NEXT_TRACK": "K_NEXT", "KC_MEDIA_PREV_TRACK": "K_PREV",
    "KC_MEDIA_STOP": "K_STOP2", "KC_CALCULATOR": "C_AL_CALC",
    # Swedish aliases: Oryx spelling -> this repo's #define spelling.
    "SE_GRV": "SE_GRAV", "SE_COLN": "SE_COLON", "SE_DQUO": "SE_DQUOT",
    "SE_SLSH": "SE_SLASH", "SE_MINS": "SE_MINUS", "SE_UNDS": "SE_UNDER",
    "SE_EQL": "SE_EQUAL", "SE_LBRC": "SE_LBRACKET", "SE_RBRC": "SE_RBRACKET",
    "SE_LCBR": "SE_LBRACE", "SE_RCBR": "SE_RBRACE", "SE_LPRN": "SE_LPAR",
    "SE_RPRN": "SE_RPAR", "SE_TILD": "SE_TILDE", "SE_DLR": "SE_DOLLAR",
    "SE_OSLH": "SE_OO",
}
# Identity-ish families filled in below.
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEYCODES[f"KC_{_c}"] = _c
for _n in range(10):
    KEYCODES[f"KC_{_n}"] = f"N{_n}"
for _n in range(1, 25):
    KEYCODES[f"KC_F{_n}"] = f"F{_n}"
for _s in ("AA ADIA ACUT AMPR APOS ASTR AT BSLS CIRC GRTR LESS PIPE PLUS QUES "
           "SECT").split():
    KEYCODES.setdefault(f"SE_{_s}", f"SE_{_s}")

# Whole-binding translations (these are behaviours, not plain keycodes).
BEHAVIOURS = {
    "KC_MS_BTN1": "&mkp MB1", "KC_MS_BTN2": "&mkp MB2", "KC_MS_BTN3": "&mkp MB3",
    "KC_MS_UP": "&mmv MOVE_UP", "KC_MS_DOWN": "&mmv MOVE_DOWN",
    "KC_MS_LEFT": "&mmv MOVE_LEFT", "KC_MS_RIGHT": "&mmv MOVE_RIGHT",
    "KC_MS_WH_UP": "&msc SCRL_UP", "KC_MS_WH_DOWN": "&msc SCRL_DOWN",
    "KC_MS_WH_LEFT": "&msc SCRL_LEFT", "KC_MS_WH_RIGHT": "&msc SCRL_RIGHT",
    "CW_TOGG": "&caps_word", "QK_BOOT": "&bootloader",
    "QK_LLCK": "&none", "RGB": "&none", "RGB_MODE_FORWARD": "&none",
}

MOD_WRAP = [("leftCtrl", "LC"), ("leftShift", "LS"), ("leftAlt", "LA"),
            ("leftGui", "LG"), ("rightCtrl", "RC"), ("rightShift", "RS"),
            ("rightAlt", "RA"), ("rightGui", "RG")]

# Oryx layer index -> ZMK layer index, for MO/TO/OSL targets.
ZMK_LAYER = {i: z for i, (_t, z, _n) in enumerate(LAYER_MAP)}
ZMK_LAYER_NAME = {0: "L_GRAPHMOD", 1: "L_SYM", 2: "L_NUM", 3: "L_RIGHT",
                  4: "L_NAV", 5: "L_VIM", 6: "L_MOUSE", 7: "L_FUNC", 8: "L_B",
                  9: "L_HEX"}   # ZMK 8 is Bluetooth, which Oryx has no equivalent for

# ------------------------------------------------------------------ fetch ---

def fetch(layout_id, revision="latest"):
    body = json.dumps({"query": QUERY,
                       "variables": {"hashId": layout_id, "revisionId": revision}})
    req = urllib.request.Request(
        ORYX_API, data=body.encode(),
        headers={"Content-Type": "application/json", "User-Agent": "kibard-sync-oryx"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        sys.exit("Oryx API error: " + json.dumps(payload["errors"], indent=2))
    layout = (payload.get("data") or {}).get("layout")
    if not layout:
        sys.exit(f"No layout {layout_id!r} returned by Oryx.")
    return layout["revision"]


def check_layers(revision):
    got = [(l["position"], l["title"]) for l in sorted(revision["layers"],
                                                       key=lambda l: l["position"])]
    want = [(i, t) for i, (t, _z, _n) in enumerate(LAYER_MAP)]
    if got != want:
        sys.exit("Oryx layers no longer match LAYER_MAP -- layers were renamed or\n"
                 "reordered. Update LAYER_MAP in this file, then re-run.\n"
                 f"  Oryx now: {got}\n  expected: {want}")

# -------------------------------------------------------------- normalise ---

COSMETIC = {"color", "glowColor", "lockGlowColor", "pristine", "swapping",
            "swapped", "detached", "icon", "emoji", "customLabel", "description"}


def meaningful(node):
    """Strip Oryx's display-only fields so recolouring a key isn't a change."""
    if not isinstance(node, dict):
        return node
    return {k: meaningful(v) for k, v in sorted(node.items())
            if k not in COSMETIC and v not in (None, False, [], {})}


def canonical(key):
    return json.dumps(meaningful(key), sort_keys=True)


def slot_label(slot):
    if not slot:
        return ""
    code = (slot.get("code") or "").replace("KC_", "")
    if slot.get("macro"):
        keys = "+".join((k.get("code") or "?").replace("KC_", "")
                        for k in slot["macro"].get("keys", []))
        code = f"macro({keys})"
    if slot.get("layer") is not None:
        code = f"{code}({slot['layer']})"
    mods = slot.get("modifiers") or {}
    prefix = "".join(n for f, n in MOD_WRAP if mods.get(f))
    return f"{prefix}-{code}" if prefix else code


def label(key):
    """One-line human label, e.g. `MO(2)>N` for layer-2-on-hold, N on tap."""
    tap, hold = slot_label(key.get("tap")), slot_label(key.get("hold"))
    dbl = slot_label(key.get("doubleTap"))
    if not tap and not hold:
        return "\u25bd"                       # no tap slot at all == transparent
    out = f"{hold}>{tap}" if tap and hold else (tap or hold)
    return f"{out}+2x{dbl}" if dbl else out


def zmk_binding(key):
    """Best-effort ZMK binding for an Oryx key. A suggestion, not a rule --
    the Kibard deliberately diverges (adaptive keys, macros, HML/HMR)."""
    tap, hold = key.get("tap") or {}, key.get("hold") or {}
    if not tap and not hold:
        return "&trans"
    if not tap:
        tap, hold = hold, {}      # hold-only key: it behaves as a plain binding

    def code_of(slot):
        c = slot.get("code")
        if slot.get("layer") is not None:
            zl = ZMK_LAYER.get(slot["layer"])
            name = (ZMK_LAYER_NAME.get(zl, f"?{slot['layer']}") if zl is not None
                    else f"<oryx layer {slot['layer']}: no ZMK counterpart>")
            if c == "MO":
                return ("mo", name)
            if c == "TO":
                return ("to", name)
            if c == "OSL":
                return ("sl", name)
        return ("kp", c)

    def kp_arg(slot):
        c = slot.get("code")
        if c in BEHAVIOURS:
            return None
        base = KEYCODES.get(c)
        if base is None:
            return None
        mods = slot.get("modifiers") or {}
        for field, name in MOD_WRAP:
            if mods.get(field):
                base = f"{name}({base})"
        return base

    if tap.get("macro"):
        keys = " ".join((k.get("code") or "?").replace("KC_", "")
                        for k in tap["macro"].get("keys", []))
        return f"<macro: {keys}>"
    if tap.get("code") == "KC_TRANSPARENT" and not hold:
        return "&trans"
    if tap.get("code") == "KC_NO" and not hold:
        return "&none"
    if tap.get("code") in BEHAVIOURS and not hold:
        return BEHAVIOURS[tap["code"]]

    kind, _ = code_of(tap)
    if kind in ("mo", "to", "sl"):
        return f"&{kind} {code_of(tap)[1]}"

    tap_arg = kp_arg(tap)
    if not hold:
        return f"&kp {tap_arg}" if tap_arg else f"<?{tap.get('code')}>"

    hkind, hname = code_of(hold)
    if hkind in ("mo", "to", "sl"):
        beh = {"mo": "lt", "to": "HT_TO", "sl": "lt"}[hkind]
        return f"&{beh} {hname} {tap_arg}"
    hold_arg = kp_arg(hold)
    return f"&mt {hold_arg} {tap_arg}"  # likely HML/HMR on the home row


def grid(revision, oryx_pos):
    """The Oryx layer folded onto the Kibard's 34 positions."""
    layer = next(l for l in revision["layers"] if l["position"] == oryx_pos)
    return [layer["keys"][i] for i in POSITION_MAP]

# ------------------------------------------------------- ZMK keymap parser ---

KEYMAP = REPO / "config" / "kibard.keymap"

# ZMK behaviours that are equivalent to a plainer form for comparison purposes:
# the Kibard uses tuned hold-taps where Oryx has the stock QMK behaviour.
EQUIVALENT = {
    "HML": "mt", "HMR": "mt", "NUM": "mt",   # tuned home-row / numpad hold-taps
    "LT_TH": "lt",                           # thumb layer-tap
    "AK_Q": "kp Q",                          # adaptive Q (N->Q sends J)
}


def parse_keymap(path=KEYMAP):
    """{zmk layer index: [34 binding strings]} from config/kibard.keymap."""
    text = re.sub(r"//[^\n]*", "", path.read_text())
    layers = {}
    for idx, block in enumerate(re.findall(
            r"display-name\s*=\s*\"([^\"]+)\";\s*bindings\s*=\s*<(.*?)>;",
            text, re.S)):
        name, body = block
        toks = body.split()
        bindings, cur = [], None
        for t in toks:
            if t.startswith("&"):
                if cur:
                    bindings.append(" ".join(cur))
                cur = [t]
            elif cur is not None:
                cur.append(t)
        if cur:
            bindings.append(" ".join(cur))
        layers[idx] = (name, bindings)
    return layers


MOD_FN = re.compile(r"\b([LR][CSAG])\((.*)\)$")


def defines(path=KEYMAP):
    """The #define shortcuts at the top of the keymap, e.g. WS_L -> LC(LA(LEFT))."""
    return dict(re.findall(r"^#define\s+(\w+)\s+(.+?)\s*$", path.read_text(), re.M))


def flatten_mods(arg):
    """LA(LC(LEFT)) and LC(LA(LEFT)) both -> 'LC+LA LEFT': nesting order is
    not meaningful, so don't report it as a difference."""
    mods = []
    while True:
        m = MOD_FN.fullmatch(arg.strip())
        if not m:
            break
        mods.append(m.group(1))
        arg = m.group(2)
    return ("+".join(sorted(mods)) + " " + arg).strip() if mods else arg


def normalise_binding(b, subs=None):
    """Collapse a ZMK binding to a form comparable with zmk_binding() output."""
    b = b.lstrip("&").strip()
    head, _, rest = b.partition(" ")
    if head in EQUIVALENT:
        head = EQUIVALENT[head]
        if " " in head:                      # e.g. AK_Q -> "kp Q"
            return head
    if head.startswith("vim_") or head in ("acut", "grav", "circ", "tilde"):
        return "macro"
    rest = rest.replace("L_GRAPHMOD", "0").replace("L_SYM", "1")
    for i, n in ZMK_LAYER_NAME.items():
        rest = rest.replace(n, str(i))
    rest = rest.replace("L_MAIN", "0")
    for name, value in (subs or {}).items():
        rest = re.sub(rf"\b{name}\b", value, rest)
    rest = re.sub(r"\bLSHFT\b", "LSHIFT", rest)
    rest = re.sub(r"\bR(CTRL|SHIFT|ALT|GUI)\b", r"L\1", rest)   # hand-agnostic
    rest = " ".join(flatten_mods(a) for a in rest.split())
    return f"{head} {rest}".strip()


def cmd_compare(args, revision):
    """Oryx vs the checked-in ZMK keymap. Best-effort: the Kibard deliberately
    diverges in places, so this is a review list, not a list of errors."""
    zmk_layers = parse_keymap()
    subs = {k: v for k, v in defines().items() if k.startswith("WS")}
    print(f"Oryx revision {revision['hashId']}  {revision['title']!r}")
    print(f"vs {KEYMAP.relative_to(REPO)}\n")
    total = 0
    for i, (title, zmk, zname) in enumerate(LAYER_MAP):
        if zmk is None or zmk not in zmk_layers:
            continue
        got_name, bindings = zmk_layers[zmk]
        if got_name != zname:
            print(f"!! ZMK layer {zmk} is named {got_name!r}, LAYER_MAP expects "
                  f"{zname!r} -- update LAYER_MAP.\n")
        if len(bindings) != 34:
            print(f"!! {got_name}: parsed {len(bindings)} bindings, expected 34 -- skipping")
            continue
        rows = []
        for pos, key in enumerate(grid(revision, i)):
            want, have = zmk_binding(key), bindings[pos]
            if want.startswith("<macro"):
                want = "&macro"
            if args.hide_blank and {want, have} <= {"&none", "&trans"}:
                continue
            if normalise_binding(want, subs) != normalise_binding(have, subs):
                rows.append((pos, label(key), want, have))
        if not rows:
            continue
        total += len(rows)
        print(f"{zname} (ZMK {zmk}, Oryx {i} {title})")
        for pos, lab, want, have in rows:
            print(f"  pos {pos:>2}   oryx {lab:<20} ~ {want:<24} zmk {have}")
        print()
    print(f"{total} position(s) differ. Expect some: adaptive keys, macros and\n"
          f"ZMK-only bindings have no Oryx equivalent. --hide-blank drops the\n"
          f"&none/&trans mismatches.")
    return 1 if total else 0

# --------------------------------------------------------------- commands ---

def draw(revision, oryx_pos, width=15):
    cells = [label(k) for k in grid(revision, oryx_pos)]
    lines = []
    for row in range(3):
        left = " ".join(f"{c:>{width}}" for c in cells[row * 10:row * 10 + 5])
        right = " ".join(f"{c:>{width}}" for c in cells[row * 10 + 5:row * 10 + 10])
        lines.append(f"  {left}   |   {right}")
    thumbs = cells[30:34]
    pad = " " * (width + 1) * 3
    lines.append(f"  {pad}{thumbs[0]:>{width}} {thumbs[1]:>{width}}   |   "
                 f"{thumbs[2]:>{width}} {thumbs[3]:>{width}}")
    return "\n".join(lines)


def cmd_show(args, revision):
    for i, (title, zmk, zname) in enumerate(LAYER_MAP):
        if args.layer is not None and i != args.layer:
            continue
        tag = f"-> ZMK {zmk} {zname}" if zmk is not None else "(no ZMK counterpart)"
        print(f"\nOryx {i} {title} {tag}")
        print(draw(revision, i))
    print()


def cmd_snapshot(args, revision):
    # Stored stripped of Oryx's display-only fields: a fifth of the size, and
    # `git diff` on the snapshot is then readable on its own.
    lean = dict(revision, layers=[dict(l, keys=[meaningful(k) for k in l["keys"]])
                                  for l in revision["layers"]])
    SNAPSHOT.write_text(json.dumps(
        {"layoutId": args.layout, "revision": lean}, indent=1, sort_keys=True) + "\n")
    print(f"Snapshot updated: revision {revision['hashId']} "
          f"({revision['title']!r}) -> {SNAPSHOT.relative_to(REPO)}")
    print("Commit it alongside the keymap change so the next diff starts here.")


def cmd_diff(args, revision):
    if not SNAPSHOT.exists():
        print("No snapshot yet -- recording the current Oryx layout as the baseline.")
        print("It assumes config/kibard.keymap is already in sync with Oryx.\n")
        cmd_snapshot(args, revision)
        return 0

    old = json.loads(SNAPSHOT.read_text())["revision"]
    print(f"Oryx     revision {revision['hashId']}  {revision['title']!r}")
    print(f"Snapshot revision {old['hashId']}  {old['title']!r}")
    if old["hashId"] == revision["hashId"]:
        print("\nSame revision -- nothing to port.")
        return 0

    total, skipped = 0, 0
    for i, (title, zmk, zname) in enumerate(LAYER_MAP):
        try:
            new_keys, old_keys = grid(revision, i), grid(old, i)
        except StopIteration:
            continue
        changes = [(p, o, n) for p, (o, n) in enumerate(zip(old_keys, new_keys))
                   if canonical(o) != canonical(n)]
        if not changes:
            continue
        if zmk is None:
            skipped += len(changes)
            print(f"\nOryx {i} {title}: {len(changes)} key(s) changed "
                  f"-- no ZMK counterpart, skipping.")
            continue
        total += len(changes)
        print(f"\n{zname} (ZMK layer {zmk}, Oryx {i} {title})")
        for pos, o, n in changes:
            print(f"  pos {pos:>2}   {label(o):>18}  ->  {label(n):<18}"
                  f"  {zmk_binding(n)}")

    # Keys outside the Kibard's 34 positions, reported so nothing is silently lost.
    mapped = set(POSITION_MAP)
    off = 0
    for i, (title, zmk, _n) in enumerate(LAYER_MAP):
        new = next(l for l in revision["layers"] if l["position"] == i)["keys"]
        prev = next((l for l in old["layers"] if l["position"] == i), None)
        if prev is None:
            continue
        off += sum(1 for j in range(len(new))
                   if j not in mapped and canonical(new[j]) != canonical(prev["keys"][j]))
    if off:
        print(f"\n({off} more key(s) changed on Voyager-only positions -- "
              f"columns and rows the Kibard doesn't have.)")

    print(f"\n{total} key(s) to port"
          + (f", {skipped} skipped" if skipped else "") + ".")
    if total:
        print("After editing config/kibard.keymap, run: tools/sync-oryx.py snapshot")
    return 1 if total else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layout", default=LAYOUT_ID, help=f"Oryx layout id (default {LAYOUT_ID})")
    ap.add_argument("--revision", default="latest", help="Oryx revision (default latest)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("diff", help="changes since the last snapshot (default)")
    sub.add_parser("snapshot", help="record the current Oryx layout as ported")
    show = sub.add_parser("show", help="draw Oryx layers in Kibard geometry")
    show.add_argument("layer", nargs="?", type=int, help="Oryx layer index")
    cmp_ = sub.add_parser("compare", help="Oryx vs the checked-in ZMK keymap")
    cmp_.add_argument("--hide-blank", action="store_true",
                      help="skip positions where both sides are &none/&trans")
    sub.add_parser("json", help="dump the raw Oryx revision")
    args = ap.parse_args()

    revision = fetch(args.layout, args.revision)
    check_layers(revision)

    if args.cmd == "json":
        print(json.dumps(revision, indent=1, sort_keys=True))
        return 0
    if args.cmd == "show":
        return cmd_show(args, revision) or 0
    if args.cmd == "compare":
        return cmd_compare(args, revision)
    if args.cmd == "snapshot":
        return cmd_snapshot(args, revision) or 0
    return cmd_diff(args, revision)


if __name__ == "__main__":
    sys.exit(main())
