# Spec: Widget slot, Arch Update Radar, Deep Space Network board

Target: Kunu's fork of end-4 `dots-hyprland` (Quickshell, "illogical-impulse"), branch `nasa-punk`.
Status: design approved (canvas rev 1.2), decisions updated 2026-10-31. Ready to implement.
Design source of truth: "NASA-punk Component Workshop" canvas → page **Rev 1.2 · Widgets**
(https://claude.ai/artifact/Qu75wmteCHPg2CcvgrtneP). Boards: `PKG-02 Update radar`, `DSN-03 Deep Space Network`, `In place · rotating slot on P1`.
Overall look and motion rules: project doc `claude/nasa-punk-design-direction.md`.

---

## 0. Ground rules for this codebase

- **Don't edit upstream files unless unavoidable.** Add new files; wire them in with as few lines as possible in existing files. Every edited upstream line is a future rebase conflict.
- **Leave `services/Updates.qml` (upstream) alone.** Build a new `services/UpdateRadar.qml` next to it.
- **No root, ever.** Nothing in these widgets runs `sudo` or installs packages on its own.
- **No invented data.** If a source is down or stale, show the "no signal" state (blinking `--:--`), never placeholder numbers.
- Keybinds, if any, go in `~/.config/hypr/custom/keybinds.lua` (Lua, Hyprland 0.55).
- Commit per layer: `slot: …`, `pkg: …`, `dsn: …`.

## 1. File layout

```
dots/.config/quickshell/ii/
├─ services/
│  ├─ UpdateRadar.qml          singleton · pacman + AUR + Arch news
│  └─ Dsn.qml                  singleton · DSN Now feed
├─ scripts/nasapunk/
│  ├─ dsn2json.py              dsn.xml + config.xml → JSON on stdout
│  └─ archnews.py              RSS → JSON on stdout
├─ modules/nasapunk/
│  ├─ common/
│  │  ├─ NasaPunk.qml          singleton · tokens (see §5)
│  │  ├─ LcdNumber.qml         DSEG7 digits + ghost "888"
│  │  ├─ TickRail.qml          ruler with optional cursor/scan
│  │  ├─ ArcSweep.qml          indeterminate loader
│  │  └─ Slip.qml              paper notification slip with stub
│  ├─ slot/
│  │  ├─ WidgetSlot.qml        360×96 container, paging, arrows
│  │  └─ SlotPager.qml         dots + ‹ › buttons
│  └─ widgets/
│     ├─ UpdateRadarSlot.qml
│     ├─ UpdateRadarPopout.qml
│     ├─ DsnSlot.qml
│     └─ DsnPopout.qml
└─ tests/fixtures/
   ├─ dsn.sample.xml           first real fetch, saved verbatim
   ├─ config.sample.xml
   └─ archnews.sample.xml
```

State files (not in the repo): `~/.local/state/nasapunk/news-read.json`, `~/.local/state/nasapunk/slot.json`.

## 2. Widget slot (shared)

**Placement:** right column of the P1 desktop, directly under telemetry, replacing the old launch slip. Size 360 × 96 logical px at 1080p. Use end-4's UI scale on the 4K monitor; don't hardcode device pixels.

**Pages, in order:** `DSN` → `PKG` → `LAUNCH`. Keep it data-driven (a list of components) so pages can be added later.

**Interaction:**
- **Mouse wheel over the slot** cycles pages: down = next, up = previous. Debounce 250 ms so one notch = one page.
- **Two small arrow buttons `‹` `›`** in the pager row under the slot (22 × 18 px, 5 px radius, 1 px border). Click = previous/next.
- **No auto-rotation timer.**
- **Click the slot body** opens that page's pop-out. `Esc` or clicking outside closes it.
- Remember the last page in `slot.json`.
- **One-time nudge:** when `UpdateRadar.state` changes to `newsHold`, jump to `PKG` once. Don't lock it there; the user can scroll away.

**Pager row:** dots on the left (active dot 22 × 4 px in SIGNAL; inactive 8 × 4 px at 25 % ink). On the right: `N / 3 · SCROLL` then `‹ ›`.

**Motion:** page change = 260 ms fade + 6 px rise, decelerating ease (`Easing.OutCubic` or a bezier like .2,.8,.2,1). No bounce. Pop-out: leader line draws (~220 ms), then the panel lands (~260 ms).

## 3. Widget A: Arch Update Radar

### 3.1 Data sources

| What | Command / URL | Notes |
|---|---|---|
| Repo updates | `checkupdates` (pacman-contrib) | Syncs a temp DB; no root. Output: `name old -> new` per line. Exit code 2 = none. |
| AUR updates | `yay -Qua` | Same line format. Skip silently if `yay` is missing. |
| Download sizes | `LANG=C pacman -Si --dbpath "${TMPDIR:-/tmp}/checkup-db-$(id -u)" <pkgs…>` | Read **checkupdates' temp DB**, not the system sync DB (that one is stale until the next real `-Syu`). Parse `Name` and `Download Size`. `LANG=C` keeps the labels English. **No new packages:** Kunu wants the system kept light. AUR packages have no size → show `BUILD`. |
| Arch news | `https://archlinux.org/feeds/news/` | RSS. Parse title, link, pubDate, first paragraph in `archnews.py`. |
| Last full upgrade | `/var/log/pacman.log` | Last line containing `starting full system upgrade`. |
| Update in progress | `/var/lib/pacman/db.lck` exists | Poll every 1 s only while state is `updating`. |
| Reboot needed | `/usr/lib/modules/$(uname -r)` missing **or** `/proc/driver/nvidia/version` ≠ installed `nvidia-utils` | Standard Arch checks. |

### 3.2 Service API (`UpdateRadar.qml`)

```qml
property string state        // nominal | checking | pending | newsHold | updating | rebootRequired | offline
property int repoCount
property int aurCount
property var packages        // [{ name, from, to, repo, sizeBytes?, flag }]
property var news            // [{ id, title, link, date, summary, requiresAction, read }]
property date lastCheck
property real updateProgress // 0–1 while updating
function refresh()
function markNewsRead(id)
function runUpdate()         // opens foot: ["foot", "-e", "yay", "-Syu"]
```

**State rules:**
- `checking` while either check process is running.
- `newsHold` if `count > 0` **and** any news item is newer than the last full upgrade **and** unread.
- `updating` while `db.lck` exists. Progress = upgraded lines appended to `pacman.log` since start ÷ pending count.
- `rebootRequired` after an update when the reboot check fires. It stays until reboot.
- `offline` if the check fails twice in a row. Show "no signal" dashes.

**Flags:** `linux*` / `nvidia*` → `REBOOT` (SIGNAL). `hyprland` → `RELOAD` (TRACE). `*-git` from AUR → `REBUILD` (TRACE). Everything else → `—`.

**`requiresAction`:** heuristic, true if the post body mentions "manual intervention", "requires", "before upgrading", or the title contains "intervention". Better to over-warn than miss one.

**Schedule:** on shell start, every 2 h (reuse upstream's `Config.options.updates.checkInterval` if present, else 120 min), on wake from suspend (hook into end-4's `Idle`/session service if available), and when the slot is clicked while `nominal`.

### 3.3 Slot layouts (see board PKG-02, row 01)

- **Nominal:** greyed LCD `000` · `PKG // SYS NOMINAL` · `CHECKED <n> MIN AGO` · `[■] UP TO DATE`
- **Checking:** `ArcSweep` + `PKG // SYNCING` + `TEMP DB · NO ROOT` + scanning `TickRail`
- **Pending:** LCD count · `PKG // <n> PENDING` · `REPO <a> · AUR <b> · <size>` · 6 px split bar (ink = repo, TRACE = AUR)
- **News hold:** hazard header `READ BEFORE UPDATE` + `<n> HELD`, news title, `MANUAL INTERVENTION · <date>`, fixed hazard-orange stub on the right
- **Updating:** LCD percent · `PKG // INSTALLING` · `<i> / <n> · <pkg>` · progress bar
- **Reboot required:** SIGNAL border · `PKG // DONE · n / n` · `RUNNING KERNEL ≠ INSTALLED` · `[R] REBOOT` button (calls `systemctl reboot` only after a hold-to-confirm, motion sheet M-11)

### 3.4 Pop-out (board PKG-02, row 02)

- Header `PKG // UPDATE RADAR` with segmented filter `ALL n | REPO n | AUR n`.
- Table columns: select `[■]`, PACKAGE, FROM → TO, SIZE (from `pacman -Si --dbpath`, `BUILD` for AUR), REPO, FLAG. Show max 6 rows, then `+ n MORE` (scrollable).
- Right column: news since last upgrade. Action-required items are paper slips with a hazard stub and `[M] MARK READ`. Info items use the header style.
- Footer: `RUNS yay -Syu IN FOOT` · `[N] NEWS` · `[U] UPDATE ALL`. **`[U]` is disabled while `newsHold`.**

## 4. Widget B: Deep Space Network board

### 4.1 Data sources

| What | URL | Refresh |
|---|---|---|
| Live state | `https://eyes.nasa.gov/dsn/data/dsn.xml?r=<unix-ms>` | 10 s while the DSN slot page or pop-out is visible; otherwise 120 s. Back off ×2 on errors up to 10 min. |
| Names / sites | `https://eyes.nasa.gov/apps/dsn-now/config.xml` | Once per day, cached to `~/.cache/nasapunk/dsn-config.xml`. |

This feed is the public data behind NASA's DSN Now page. It's unofficial (no API contract), so keep parsing defensive and fixture-tested.

**Fields** (attribute names, from the feed; cross-checked with the go-dsn-now client):
- `station`: `name`, `friendlyName`, `timeUTC`, `timeZoneOffset`
- `dish`: `name`, `azimuthAngle`, `elevationAngle`, `windSpeed`, `isMSPA`, `isArray`, `isDDOR`, `activity`
  - `upSignal` / `downSignal`: `active`, `signalType`, `dataRate`, `frequency`, `band`, `power`, `spacecraft`, `spacecraftID`
  - `target`: `name`, `id`, `uplegRange`, `downlegRange`, `rtlt`
- `config.xml`: `sites>site` (`name`, `friendlyName`, `longitude`, `latitude`, `dish` with `name`, `friendlyName`, `type`) and `spacecraftMap>spacecraft` (`name`, `explorerName`, `friendlyName`)

⚠️ **Verify on the first fetch** how dishes attach to stations (nested, or listed after their station in order). Save that response as `tests/fixtures/dsn.sample.xml` and write the parser against it.

### 4.2 Parser (`dsn2json.py`)

Python 3 stdlib only (`urllib`, `xml.etree.ElementTree`). Prints one JSON object:

```json
{ "fetchedAt": "...", "complexes": [ { "code": "GDS", "name": "Goldstone", "lon": -116.9,
  "localTime": "...", "dishes": [ { "name": "DSS-14", "size": "70 M", "az": 172, "el": 38,
  "activity": "...", "up": true, "down": true, "band": "X", "dataRateBps": 160,
  "powerDbm": -158, "target": "Voyager 1", "rtltSec": 169200, "rangeKm": 0, "idle": false } ] } ],
  "links": 6, "farthest": { "dish": "DSS-14", "target": "Voyager 1", "rtltSec": 169200 } }
```

- Resolve spacecraft codes to friendly names via `spacecraftMap`. Fall back to the raw code.
- `idle` = no target, or no active up/down signal.
- `rtlt` and ranges can be `-1` or empty. Treat those as unknown and omit them from the UI.
- Exit non-zero on fetch or parse failure. The service then flips to the stale state.

### 4.3 Service API (`Dsn.qml`)

```qml
property var complexes
property int linkCount
property var farthest
property date fetchedAt
readonly property bool stale: (now - fetchedAt) > 60 s
property bool active         // set by the slot/pop-out when visible; controls the 10 s vs 120 s poll
```

### 4.4 Slot (board DSN-03, "01 // SLOT")

- Row 1: `DSN // <n> LINKS` · `GDS a · MAD b · CAN c`
- Row 2: pulsing `▼` (SIGNAL) · farthest target name · `<dish> · <BAND>`
- Row 3: `RTLT ~<h> H` · `<rate>` · `FARTHEST`
- When stale: replace the values with blinking `--:--` and `NO SIGNAL`.

### 4.5 Pop-out (board DSN-03, rows 02–03)

- **Earth strip:** the three complexes on a −180…180° longitude rail, a sun marker at the subsolar longitude (compute from UTC), and a night band.
- **Three columns** (Goldstone · Madrid · Canberra) with local time. Each dish row has:
  - a dish glyph rotated by elevation: `rotate(-(90 - el) * 0.6)`, pedestal fixed
  - `DSS-xx · <size>` and `AZ · EL`
  - `▲` lit in TRACE when the uplink is active, `▼` lit in SIGNAL when the downlink is active, dim otherwise
  - target friendly name, band, data rate, RTLT
  - Idle dishes at 40 % opacity, labeled `IDLE · STOW`.
- **Selected link panel:** defaults to the farthest; click any dish row to select it. Shows a large RTLT LCD (`HH:MM:SS`), "THE BITS ON SCREEN LEFT THE CRAFT ~<rtlt/2> AGO", range and power.

## 5. Theme tokens (`NasaPunk.qml`)

Until the wallpaper color pipeline lands, hardcode W6 light values and keep everything behind tokens:

```
signal  #bc3830   trace   #76605d   tint    #f5eceb   tint2  #e8dfde
ink     #111111   dim     #555555   rule    ink @16 %  ghost  ink @8 %
paper   #eeeeec   housing #a7abae   graphite #26292c  hazard #ff5a1f (fixed)
fonts   label "Departure Mono" · numerals "DSEG7 Classic" Bold · body "IBM Plex Mono"
radius  6 control · 12 card · 16 slot · 20 panel · 999 pill
motion  fast 120 · base 220 · panel 260 · dock 320 ms, decelerating, no bounce
```

Fonts: Departure Mono and DSEG are both on the AUR or GitHub (MIT / OFL). Add them to the install notes.

## 6. Acceptance checklist

- [ ] Slot pages change on wheel (one notch = one page) and on `‹ ›`. No timer rotation.
- [ ] Last page is restored after `qs` restart.
- [ ] PKG: every state reachable via fixtures or a debug toggle; `[U]` disabled under `newsHold`; nothing ever runs as root.
- [ ] PKG: reboot state appears after a kernel update and clears after reboot.
- [ ] DSN: parses `tests/fixtures/dsn.sample.xml` offline; friendly names resolve; stale state shows after 60 s of failed fetches.
- [ ] DSN polls at 10 s only while visible; 120 s otherwise.
- [ ] Both widgets idle under ~1 % CPU on the NUC.
- [ ] No upstream file changed except the one line that mounts `WidgetSlot` into the right column.

## 7. Decisions and open questions

Decided (2026-10-31):
1. **Reboot button stays.** `[R] REBOOT` in the reboot-required state, behind hold-to-confirm (1.2 s, release cancels), then `systemctl reboot`.
2. **No new dependencies.** Sizes come from `pacman -Si --dbpath` against checkupdates' temp DB; `expac` is not used.

Still open (default if Kunu doesn't answer: no):
3. Should the DSN pop-out also list spacecraft not currently in contact? The feed only reports live contacts, so this would need a hand-kept list.

## References

- Design canvas, page Rev 1.2 · Widgets: https://claude.ai/artifact/Qu75wmteCHPg2CcvgrtneP
- Project doc: `claude/nasa-punk-design-direction.md` (Arch Rice project)
- end-4 dots-hyprland: https://github.com/end-4/dots-hyprland (see `services/Updates.qml`, `services/Weather.qml` for the Process/Timer pattern)
- Quickshell docs: https://quickshell.outfoxxed.me/docs/ (`Quickshell.Io` → `Process`, `StdioCollector`, `FileView`)
- Arch news RSS: https://archlinux.org/feeds/news/
- `checkupdates` (pacman-contrib): https://man.archlinux.org/man/checkupdates.8
- DSN Now: https://eyes.nasa.gov/apps/dsn-now/
- go-dsn-now (field names and endpoints reference): https://github.com/RustyDaemon/go-dsn-now
