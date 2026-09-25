---
name: testing-midi-pocket
description: How to run and drive the MIDI Pocket web app (site/) for E2E testing — static serving, CDP quirks on this box, MP debug handle, file-import automation, and env font fixes.
---

# Testing MIDI Pocket (site/ web app)

## Serve + launch
- Serve with `python3 -m http.server 8000 --bind 127.0.0.1` from `site/` (no backend needed).
- Launch Chrome on :0: `google-chrome --remote-debugging-port=9222 --autoplay-policy=no-user-gesture-required --user-data-dir=/tmp/<profile> --no-first-run --no-default-browser-check --start-maximized http://127.0.0.1:8000/`.
- The `--autoplay-policy` flag lets AudioContext run without a gesture (needed for scripted tests). A REAL click still unlocks audio without it — verify the gesture path with a second flag-less Chrome if needed.

## CDP gotchas on this box
- **Port 127.0.0.1:9222 is an `adb` forward** to the Android emulator — your Chrome ends up on `[::1]:9222` instead. List targets at `http://[::1]:9222/json`; hit `127.0.0.1:9222` and you'll get the emulator's browser by mistake.
- websocket-client must use `suppress_origin=True` or Chrome 137 rejects the WS handshake (403 "Rejected an incoming WebSocket connection").
- Chrome binds the debug port on EITHER ipv4 127.0.0.1 or ipv6 ::1 — check `ss -tlnp | grep <port>` if one address fails.

## Fonts (Japanese UI)
The box has NO CJK or emoji fonts — Japanese + icon glyphs render as tofu boxes in recordings. Fix per-user, no sudo:
- JP: download `NotoSansJP[wght].ttf` from github.com/google/fonts → `~/.local/share/fonts/` → `fc-cache -f`.
- Emoji: download the Debian `fonts-noto-color-emoji_*_all.deb` from deb.debian.org, `ar x` + `tar -xf` the data, copy `NotoColorEmoji.ttf` to `~/.local/share/fonts/`.
- **Restart Chrome after installing** (fontconfig cache is per-process — reload alone is not enough).

## App internals for assertions
- `window.MP = {player, state, db}` — use `MP.state.tracks/filtered/fonts/fontId/queue/qpos/favs/recent`, `MP.player.seq.currentTime/.paused/.playbackRate`, `MP.player.synth._voiceCount`, `MP.player.ctx.state`.
- Catalog loads progressively (`catalog/part-*.json`); list virtualizes 60 rows via IntersectionObserver on `#listSentinel` — `MP.state.renderLimit` grows on scroll.
- File import: hidden inputs `#fileMidi` / `#fileFont` — drive via CDP `DOM.getDocument` → `DOM.querySelector` → `DOM.setFileInputFiles` with a host path (works headed).
- Persistence: favs/recent/font/tempo in localStorage (`mp_*` keys); imported midis/fonts in IndexedDB `midi-pocket-db` (stores `userMidi`, `userFonts`).
- Service worker `mp-v2`: precaches shell + catalog.json + fonts.json; runtime-caches parts/midi/soundfonts ONLY after first fetch — so offline playback works only for previously-played tracks and a previously-loaded font. `Network.emulateNetworkConditions(offline)` does NOT cover the SW's own fetches — for true offline testing kill the web server instead.
- `seq.loopCount = 1` in app.js means each song plays ~twice before `songEnded` auto-advances.

## Known pitfall to re-check in future versions
- The `timeChange` event payload is a bare number; if the seek bar/elapsed label stays frozen, check that `onTime` reads the event value, not `e.time`.
