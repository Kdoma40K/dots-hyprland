# NASA-punk shell: Claude Code handoff

**Owner:** Kunu · **Machine:** Arch Linux PC (never the MacBook; that one is Riddhi's)
**Status:** design approved through canvas rev 1.2 · handoff written 2026-10-31
**Goal:** fork end-4's dots-hyprland (Quickshell "ii" shell) and turn it into a NASA-punk / cassette-futurist industrial sci-fi desktop. It replaces Panacea Shell.

Read this whole file before writing code. The widget spec lives next to it at `docs/specs/widgets-update-radar-dsn.md`.

---

## 1. How to work with Kunu

- He knows QML basics but treats files like YAML configs. When you touch something new (property bindings, `Process`, `Singleton` services, Hyprland 0.55's Lua config), give a short refresher on **why** it works, not just what to paste.
- Mentor tone, explain trade-offs, push back bluntly when something is a bad idea.
- **Ask before** running parallel agents, adding a dependency, or doing anything that can't be undone.
- End each session with what changed, how to test it, and the next step.

## 2. Ground rules (non-negotiable)

1. **Fork, don't patch in place.** Edit in the repo, never directly in `~/.config`. Deploy with `./setup install-files`.
2. **Add new files instead of editing end-4's** wherever possible (new `modules/nasapunk/…`, new services). Keeps rebases cheap. When you must edit an upstream file, keep the diff small and leave a `// nasa-punk:` comment.
3. **Hyprland overrides go in `~/.config/hypr/custom/*.lua`** (in the repo: the matching `custom/` source). end-4 binds **SUPER+D** to maximize. Unbind it in `custom/keybinds.lua` before reusing it for LOAF.
4. **No new packages.** Kunu wants the system light. Use what's already installed: pacman, checkupdates (pacman-contrib), yay, python3 stdlib, curl, Quickshell. If something truly needs a new package, stop and ask.
5. **Never invent data.** A widget with no data shows a blinking `--:--` or `NO SIGNAL`. No placeholder numbers in shipped code.
6. **Widgets never run as root and never auto-update.** Reading is fine (checkupdates uses a temp DB). Upgrading is always Kunu's choice from a terminal.
7. **Every commit leaves a working shell.** If Quickshell fails to load, `qs -c ii` from a terminal shows the error. Keep a known-good tag to fall back to.

## 3. Git workflow

```bash
git clone https://github.com/<kunu>/dots-hyprland.git && cd dots-hyprland
git remote add upstream https://github.com/end-4/dots-hyprland.git
git config rerere.enabled true          # remembers how you resolved a conflict
git config merge.conflictStyle zdiff3   # shows the base version inside conflicts
git switch -c nasa-punk

# updating from end-4 later:
git fetch upstream
git rebase upstream/main                # conflicts stop here for manual review
./setup install-files
```

Commits sit on top of upstream. When a rebase stops on a conflict, show Kunu the three-way view and decide together.

## 4. Kunu's environment

| | |
|---|---|
| Hardware | Intel NUC 11 Extreme, RTX 3070 (nvidia 610), 32 GB |
| Display | ASUS 27" 4K 240 Hz **QD-OLED**, HDMI-A-2, scale 1.0 (care about burn-in) |
| OS | Arch, kernel 7.0.x, dual-boots Windows |
| WM | Hyprland 0.55 (Lua config) |
| Shell / term | fish, foot |
| Apps | VS Code (Code-OSS), Vivaldi |
| Already running | SDDM (custom theme), hyprsunset, cliphist, voxtype |

## 5. Design direction (summary)

The full direction is `claude/nasa-punk-design-direction.md` in the Arch Rice project. In short:

**Look.** Rounded containers (radii 6 / 12 / 20 / pill) with technical insides: tick rails, LCD numerals, hazard stripes, leader lines, serial labels. Mid-grey housings, not pure Nothing-style white/black.

**Color.**
- Three adaptive slots pulled from the wallpaper in OKLab and clamped: **SIGNAL** (accent), **TRACE** (secondary), **TINT** (panel fill). Prototype: `scripts/trio.py` (included).
- Light/dark picked automatically from wallpaper brightness under the bar.
- Fixed tokens: hazard `#ff5a1f`, fallback signal `#d71921`, paper `#eeeeec`, housing `#a7abae`, graphite `#26292c`.

**Type.** Departure Mono for labels, DSEG7 for numerals (with a ghost `88:88` behind), IBM Plex Mono for body text. No Doto.

**Island.** A compound dynamic island at the top center, like end-4's but reskinned. Pop-outs hang directly under their parent pill. Quick access to Wi-Fi, Bluetooth, power menu and settings stays one click away (the part Kunu loved in Panacea).

**Greebles.** Decoration that carries real data (clock seconds, CPU, uptime, orbit). It hides when a panel opens, takes no input, and drifts and dims slowly to protect the OLED.

**Motion.** Decelerating, no bounce, 120–320 ms. Load states: LCD count-up, arc sweep, tick scanner, square-pip wave, blinking `--:--`, leader-line draw, slip in/out, scrolling scope, hold-to-fill, boot log.

**Visualizer.** Oscilloscope trace everywhere (Cava is already part of end-4).

**Desktop.**
- **P1 Mission Control** is the daily layout: island on top, right column with telemetry, widget slot and launch bay.
- **P3 Observatory** is the orbit widget's expanded state and the idle screensaver.
- **P4 Co-pilot (LOAF mode)** is a docked Claude panel (see phase 7).
- P2 was dropped (clock too large).

**Mascot.** LOAF-01, the head-only pixel cat from canvas rev 0.5. Full-body versions were scrapped. Don't bring them back.

**Lock / login.** The lock reskins end-4's Quickshell session lock (`WlSessionLock`). Login is a separate SDDM QML theme with the same look.

## 6. Build plan

Do the phases in order. Each phase ends with a commit, a short note to Kunu, and screenshots if possible.

### Phase 0: Setup and backup
- Back up `~/.config/{hypr,quickshell}` and the Panacea config to a dated tarball.
- Fork, clone, set up remotes and git config (section 3).
- Tag the clean upstream state `base-upstream`.

### Phase 1: Stock end-4 on NVIDIA
- Install stock end-4 per its wiki. Confirm Hyprland, Quickshell, the bar, the lock and Cava all work on the 3070 at 4K/240.
- Note any NVIDIA env vars needed and put them in `custom/`.
- Keep Kunu's existing hyprsunset, cliphist and voxtype binds working.
- Tag `stock-ok`.

### Phase 2: Theme tokens, fonts, colors
- Add `modules/nasapunk/common/NasaPunk.qml` (singleton): radii, spacing, motion durations and easing, fixed colors, font families. Map them onto end-4's `Appearance.qml` where they overlap rather than duplicating.
- Fonts in `~/.local/share/fonts` (user-level, not a package): Departure Mono, DSEG7, IBM Plex Mono.
- Port `trio.py` into end-4's color pipeline (`scripts/colors/switchwall.sh` → palette generation). Output SIGNAL/TRACE/TINT plus light/dark mode into the JSON the shell already reads. Python stdlib only.
- Test against the six wallpapers Kunu shared (ask him for the files).

### Phase 3: Island and panels
- Reskin the bar into the compound island. Pop-outs hang under their parent.
- Wi-Fi, Bluetooth, power menu and settings stay reachable from the island.
- Use end-4's existing services for data; only the visuals change.

### Phase 4: Right column
- Telemetry block (CPU, GPU, RAM, temps: real values only).
- **Widget slot**, built exactly to `docs/specs/widgets-update-radar-dsn.md`:
  - 360×96, pages DSN → PKG → LAUNCH.
  - Mouse wheel (250 ms debounce) plus small ‹ › arrows. No auto-rotate timer.
  - Remembers the last page. Jumps once to PKG when an Arch news hold appears.
  - Update Radar: checkupdates + `yay -Qua`, sizes via `LANG=C pacman -Si --dbpath "${TMPDIR:-/tmp}/checkup-db-$(id -u)"`, Arch news RSS, reboot-required check. **The reboot button stays**, behind a 1.2 s hold-to-confirm.
  - DSN Now: parsed with stdlib `dsn2json.py`. Poll every 10 s when visible, 120 s otherwise. Verify station/dish nesting against the first real fetch.
- Launch bay (Launch Library 2 next launch, countdown in DSEG7).

### Phase 5: Orbit and Observatory
- ISS position (wheretheiss.at or Open Notify) and sun/moon (astronomy-engine, or a small stdlib port).
- Expanded state = P3 Observatory. Reuse it as the idle screensaver via hypridle.

### Phase 6: Greebles
- Data-bearing decoration around the clock, island and column. Hide when panels open, no input, slow drift and dim (OLED).

### Phase 7: LOAF dock (P4 Co-pilot)
- A Quickshell `PanelWindow` on the right with an **exclusive zone** of 1/4 to 1/5 of the screen width so Hyprland re-tiles windows beside it.
- Toggle: SUPER+D (after unbinding end-4's maximize).
- Start simple: an embedded foot terminal running `claude`. Check the current Claude Code CLI flags (`claude --help`) before any deeper integration. Don't assume flags.
- LOAF-01 head sprite sits in the dock header with idle/thinking/done states.

### Phase 8: Lock, then login
- Lock: reskin end-4's `modules/ii/lock` (big DSEG7 clock, ghost digits, hold-to-fill on unlock).
- Login: a new SDDM QML theme matching the lock. Ask before touching `/etc` or SDDM config (needs root, so Kunu runs those steps himself).

### Phase 9: README and in-shell manual
- Kunu said he never knew everything Panacea could do. Write a proper README: every keybind, every panel, what each widget shows and where its data comes from.
- Add an in-shell manual overlay on **SUPER+/**.

## 7. Revision index (design canvas)

**Canvas:** https://claude.ai/artifact/Qu75wmteCHPg2CcvgrtneP. Ask Kunu to export screenshots or share access if you can't open it.

| Rev | What it settled | Boards |
|---|---|---|
| 0.1 | First pass, Nothing-leaning | Main, AiPanel, Toggles, Buttons, QuickTiles, Notification, Clock, Bar |
| 0.2 | Foundations, compound island | R2Foundations, R2Island, R2Kit |
| 0.3 | Orbit, first mascot (off-center pop-outs rejected) | R3Foundations, R3Island, R3Orbit, R3Mascot |
| 0.4 | Wallpaper color pipeline, desktop kit | R4Pipeline, DesktopKit, W1–W6 |
| 0.5 | Greebles, **LOAF-01 head sprite (final mascot)** | R5Greebles, R5Cat, W6g, W5g |
| 0.6 | Oscilloscope visualizer chosen, lock kit | R6Viz, LockKit, Lock1, Lock2, W6x, W5s |
| 0.7 | Lock, login, LOAF mode | Lock3, Login1, LoafMode, W6L, W5o |
| 0.8 | Desktop proposals (P1, P3, P4 kept; P2 dropped) | P1, P2, P3, P4 |
| 0.9 | Interactive prototype, motion and load states | R9Proto, R9Motion |
| 1.2 | **Widgets**: Update Radar, DSN, rotating slot | R12Radar, R12DSN, R12Desk |

Revisions 1.0–1.1 (full-body LOAF) were scrapped and removed.

**Project docs (claude.ai project "Arch Rice"):**
- `claude/nasa-punk-design-direction.md`: full design direction
- `claude/spec-widgets-update-radar-dsn.md`: widget spec (same as `docs/specs/…`)
- `claude/HANDOFF.md`: this file

## 8. References

**Base**
- end-4 dots-hyprland: https://github.com/end-4/dots-hyprland
- end-4 wiki: https://ii.clsty.link
- Files to study: `services/Updates.qml` (Process + Timer pattern), `services/Weather.qml`, `modules/common/Appearance.qml`, `modules/common/Config.qml`, `scripts/colors/switchwall.sh`, `modules/ii/lock/`, `hypr/hyprland/keybinds.lua`
- Quickshell docs: https://quickshell.org/docs/
- Hyprland wiki: https://wiki.hypr.land

**Fonts**
- Departure Mono: https://departuremono.com
- DSEG: https://github.com/keshikan/DSEG
- IBM Plex Mono: https://github.com/IBM/plex

**Data**
- DSN Now feed: https://eyes.nasa.gov/dsn/data/dsn.xml (add `?r=<ms>`), config: https://eyes.nasa.gov/apps/dsn-now/config.xml
- go-dsn-now (field reference): https://github.com/dmhutchinson/go-dsn-now (verify the path if it moved)
- Arch news RSS: https://archlinux.org/feeds/news/
- checkupdates: `man checkupdates` (pacman-contrib)
- Launch Library 2: https://ll.thespacedevs.com/docs/
- ISS position: https://wheretheiss.at/w/developer · http://open-notify.org
- astronomy-engine: https://github.com/cosinekitty/astronomy

## 9. Files in this handoff

```
CLAUDE.md                                 → repo root
docs/HANDOFF.md                           → this file
docs/specs/widgets-update-radar-dsn.md    → widget spec
scripts/nasapunk/trio.py                  → wallpaper → SIGNAL/TRACE/TINT prototype
```
