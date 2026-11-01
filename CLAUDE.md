# CLAUDE.md: nasa-punk fork of end-4/dots-hyprland

You're working with **Kunu** on his Arch Linux PC. This repo is his fork of end-4's dots-hyprland, being reskinned into a NASA-punk / cassette-futurist shell.

**Start here:** read `docs/HANDOFF.md` in full, then `docs/specs/widgets-update-radar-dsn.md` before touching the widgets.

## Rules
- Work on the `nasa-punk` branch. Commits sit on top of `upstream/main`; rebase, never merge.
- Prefer **new files** (`modules/nasapunk/…`, new services) over editing end-4's. Mark unavoidable upstream edits with `// nasa-punk:`.
- Hyprland overrides go in `custom/*.lua`. Unbind end-4's SUPER+D before reusing it.
- **No new packages.** Ask first if one seems necessary.
- **Never invent data.** Missing data shows `--:--` / `NO SIGNAL`.
- Widgets never run as root and never auto-update.
- Deploy with `./setup install-files`; don't edit `~/.config` directly.
- Every commit must leave a shell that loads (`qs -c ii` shows errors).

## Working style
- Explain the why. Give QML / Hyprland-Lua refreshers when something is new to him.
- Ask before parallel agents, new dependencies, root steps, or anything irreversible.
- End each session with: what changed, how to test, next step.

## Design canvas (source of truth for look + motion)
- Live: https://claude.ai/artifact/Qu75wmteCHPg2CcvgrtneP. Claude Code on Kunu's account can read it with the Artifact tool (`read` + `path: "project/<Board>.dc.html"`).
- Snapshot: `docs/design/canvas/` (pulled 2026-10-31, canvas version 1793512911-3e2d). `canvas.json` maps each board to its revision page and title.
- Motion and keyframes: `R9Motion`, `R9Proto`, `R12Radar`, `R12DSN`, `R12Desk`. Port their timings into QML; don't eyeball them.
- If the live canvas has changed since the snapshot, re-pull and commit as `docs: refresh canvas snapshot`.

## Environment facts (verified 2026-10-31; the handoff is older)
- Hyprland **0.56.2** (not 0.55), nvidia **615**. Check Lua config syntax against 0.56.
- Dev and test user: **ricetest** (Kunu's main user `kdoma` stays on Panacea). Clone lives at `~ricetest/dots-hyprland`; fork is `github.com/Kdoma40K/dots-hyprland`.
- Stock end-4 already installed and working for ricetest (Phase 1 confirmed by Kunu).
- `pacman-contrib` (checkupdates) approved as the one exception to "no new packages".
- `python-numpy` and `python-pillow` are already installed system-wide, so `trio.py` can keep using them.

## Comment style (Kunu's request)
Concise code, generous comments. Each new file opens with a header: what it is, what it reads, what reads it. Comment every binding, `Process` and `Timer` with *why* it exists so the data flow can be followed without a debugger.

## Current phase
Phase 0 (setup and backup): fork, branch, `base-upstream` tag and handoff docs done from kdoma. Next: in ricetest, back up configs, clone, then Phase 2. Update this line as phases finish.
