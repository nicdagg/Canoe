# Canoe Hull Designer

Design a canoe in your browser: shape the hull with sliders, see the lines plan and a 3D view, check stability, drag and behaviour in waves, and plan a foam plug, mold and laminate for building it.

**Open it:** https://nicdagg.github.io/Canoe/

## Put it on your iPhone home screen

1. Open the link above in **Safari**.
2. Tap the **Share** button (the square with an arrow pointing up).
3. Scroll down and tap **Add to Home Screen**, then **Add**.

It then opens full screen like an app, and works without signal once it has been opened once. Saved designs stay on that phone.

## Install it on a Windows PC

1. Open the link above in **Edge** or **Chrome**.
2. Click the small **install** icon at the right end of the address bar (a screen with a plus or arrow), or open the **…** menu and choose **Apps → Install this site as an app** (Edge) or **Cast, save and share → Install page as app** (Chrome).
3. Click **Install**. It gets its own window, a Start menu entry, and can be pinned to the taskbar.

Saved designs are kept in each browser separately, so designs saved on the phone don't show up on the PC.

## Ask Claude (optional)

The **Ask Claude** button lets you ask questions about your design in plain words and have Claude test changes for you. It is the only part that costs money and the only part that sends anything off your device. It needs your own Anthropic key from https://platform.claude.com, which is billed per question (the page shows a running total). The key is kept in that one browser and is never part of this repository. Everything else works without it.

## What's here

- `index.html` – the whole designer in one page. It is built from `src/designer.html`, so edit that file and never `index.html` directly
- `src/designer.html` – the designer's source
- `tools/` – `build.py` turns the source into `index.html`; `sync_conditions.py` copies the water types from the Python kit into the page
- `tests/` – automatic checks (see below)
- `manifest.webmanifest`, `sw.js`, `icons/` – what makes "Add to Home Screen" work and lets it open offline
- `python-kit/` – the Python analysis and optimizer kit (see its README); not needed for the web app

## Changing the designer

```
python3 tools/sync_conditions.py          # only if python-kit/conditions.json changed
python3 tools/build.py src/designer.html index.html
node tests/run.js                         # engine, laminate and mold maths
python3 tests/compare_kit.py              # the page and the Python kit give the same numbers
node tests/smoke.js                       # clicks through every panel in a real browser (needs Playwright)
node tests/ask.js                         # Ask Claude panel against a stand-in service (no key, no cost)
```

`tests/save_mold_zip.js` and `tests/check_mold_files.py` download a mold zip and confirm every foam tile is a closed solid and the drawings open cleanly.
