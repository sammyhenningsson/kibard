---
name: sync-voyager
description: Port changes made to the ZSA Voyager layout in Oryx into the Kibård ZMK keymap. Use when the user says they changed their Voyager or Oryx layout, or asks to sync, port or mirror those changes here.
---

# Sync the Voyager layout into Kibård

The Kibård keymap is a hand-port of the Voyager layout kept in Oryx. This
ports whatever changed in Oryx since the last sync and leaves the result in
the working tree for review. The "Staying in sync with the Voyager" section of
`CLAUDE.md` explains the tooling.

Run every command from the repo root.

## 1. Diff

```
tools/sync-oryx.py
```

It exits 1 when there are keys to port, which is the normal case, and lists
each as `pos N  old -> new  <suggested ZMK binding>`. If it says there is
nothing to port, tell the user and stop — they may not have compiled the
layout in Oryx yet, since only a compiled revision is visible to the script.

If the script fails an assertion on `POSITION_MAP` or `LAYER_MAP`, a layer was
renamed, added or reordered in Oryx. Stop and show the user the error; fixing
the tables is a decision about the port, not a mechanical step.

## 2. Port

Edit `config/kibard.keymap`, one listed key at a time. Positions count
left to right, top to bottom: 0–9, 10–19, 20–29, then thumbs 30–33.

- The suggested binding is a starting point. Look at what the position holds
  now and at its neighbours, and keep the Kibård's own wrapper when the key
  has one (`&HML`/`&HMR` home-row mods, `&NUM`, `&LT_TH`, `CAP()`), changing
  only the keycode inside it.
- Use the `SE_*` defines at the top of the keymap for Swedish symbols. If the
  script prints an unknown name such as `<?SE_MU>`, find or add the define.
- Keep the column alignment of the binding tables: pad with spaces so the
  next binding stays in its column.
- The Kibård differs from the Voyager on purpose in places: the lock keys at
  position 3, the mouse speed layers, some thumb keys, Backspace/Delete on
  the Numpad, Mouse and Navigate layers, and adaptive keys. When an Oryx
  change lands on one of these, do not overwrite it — ask the user which
  side should win.
- A change that needs a new behaviour, macro or adaptive key is more than a
  binding swap. A new `AS_*` or `AK_*` key also needs an `EQUIVALENT` entry
  in `tools/sync-oryx.py` and a label in `tools/keymap-drawer.yaml`.

## 3. Audit

```
tools/sync-oryx.py compare --hide-blank
```

This lists every remaining Oryx-vs-keymap difference. The intentional ones
from step 2 will still be there; check that none of the positions just ported
appear, and that nothing new has shown up on the layers that were touched.

## 4. Render the layer images

```
tools/render-layer-images.sh
```

It redraws all layers; only the PNGs of edited layers should show up as
modified in `git status`. If keymap-drawer or `rsvg-convert` is missing, say
so and carry on — the images are for the layer-display companion and do not
affect the firmware.

## 5. Record the snapshot

```
tools/sync-oryx.py snapshot
tools/sync-oryx.py
```

The second run must report nothing to port. Only take the snapshot once every
listed key is ported or the user has decided to leave it: the snapshot is the
baseline for the next diff, so a key skipped here is never reported again.

## 6. Update the docs

If a change touches something `CLAUDE.md` describes — a layer's activation
key, the lock keys, adaptive keys, where å/ä/ö live — update that text.
Plain symbol or shortcut moves need no doc change.

## 7. Report and stop

Do not commit or push. Pushing builds the firmware, and the user reviews the
port first. End with:

- a table of the ported keys: layer, position, was, now;
- anything left unported or decided against, and why;
- the files modified.

Then wait for the user to ask for the commit. When they do, the keymap,
`tools/oryx-snapshot.json` and the re-rendered images go in one commit.
