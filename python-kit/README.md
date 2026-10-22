# Canoe hull analysis

A Python toolkit that takes a hull from the Canoe Hull Designer and works out how it
floats, how stable it is, how hard it is to paddle, and how it rides in waves, then
scores it for a type of water and can search the sliders for a better shape.

It uses the designer's own hull equations (ported line for line from the artifact),
so a shape here is exactly the shape you see there. The settings file is the same
format as the hull and hydro sections of `config/default.json` in the PC project.

## The loop

1. **Shape it by eye** in the designer. Click *Copy settings*.
2. **Save** what you copied as `designs/<name>.json`.
3. **Compare** it with other designs in the water you care about:
   `python -m canoe_analysis analyze designs/mine.json designs/tripper.json -c big-lake-chop`
   This writes `results/<names>/<condition>/report.md` with a table and plots.
4. **Search** for a better shape for that water, holding length and load fixed:
   `python -m canoe_analysis optimize designs/mine.json -c big-lake-chop`
   This writes `results/opt-mine-big-lake-chop/best.json` and a before/after report.
5. **Look at it**: paste `best.json` into *Load settings* in the designer, check the
   lines and the 3D view, adjust anything that looks wrong, and copy it back out.
6. Repeat, or run `python -m canoe_analysis matrix designs/*.json` to see every
   design scored in every kind of water at once.

Setup: Python 3.9+ with `numpy` and `matplotlib` (`pip install numpy matplotlib`).
Run commands from this folder. For the optimizer, set `OMP_NUM_THREADS=1` first; it
already runs one design per CPU core and extra numpy threads only slow it down.
One design takes about a quarter of a second; a default search (30 generations of 28
designs) takes one to two minutes on four cores.

## In the designer

The designer's **Analyze** button runs the same analysis and scoring in the browser
(a JavaScript port of this kit, checked to match it within 0.3%), with the same eight
water profiles, a score for every profile at once, and a built-in optimizer that
searches the sliders you pick and lets you apply or undo the result. Use this kit
when you want custom profiles, asymmetric (unlinked) searches, reports and plots,
or batch comparisons. If you change `conditions.json`, the designer keeps its own
copy of the profiles until it is republished.

Two views exist only in the designer: *Wave pattern* (the Kelvin wake drawn from the
same Michell source distribution, at any speed) and *Motion in waves* (an animation in
regular waves of any height, period and direction, with roll simulated on the hull's
own righting-moment curve so it shows water over the gunwale and capsizes).

## What it calculates

| Area | Method | Main outputs |
|---|---|---|
| Hydrostatics | Exact integration of closed section polygons, with free trim if you give a centre of gravity position | draft, freeboard, waterline length and beam, Cb, Cp, Cm, Cwp, LCB, LCF, KB, BM, KM, wetted area (true 3D mesh), pounds per inch |
| Stability | Righting arm (GZ) at each heel angle by direct integration, displacement held | GM, righting moment at 10°, peak and its angle, angle where the gunwale goes under, secondary stability ratio, area under the curve |
| Calm-water drag | ITTC-1957 friction with a Hoerner form factor, plus Michell thin-ship wave drag extended to finite water depth | drag at cruise (averaged over ±0.5 mph to avoid rewarding a lucky hollow), wave-making share, speed held at a power budget, power curve |
| Wind | Head-on hull windage above the waterline | added drag in a headwind, side area for crosswind drift |
| Waves | Heave and pitch strip theory in head seas (Lewis sections, Grim damping, Gerritsma-Beukelman form) in a JONSWAP sea | significant heave and pitch, chance a wave reaches the bow sheer, added drag in waves |
| Handling | Lateral plane (underwater profile) | turn index (higher holds a line, lower spins), end immersion, total rocker |

The load model (in `stability.load_case`): the hull's centre of gravity at 45% of its
depth, 85% of the payload is crew and 15% gear 4 in off the bottom. Crew height is
set by posture: kneeling 11 in, low seat 14.5 in, seated is the seat (3.5 in below the
gunwale) plus 8 in. All of these can be overridden per condition under `load`, for
example `{"crew_lb": 340, "crew_vcg_in": 16, "gear_lb": 60, "lcg_in": -4}`, where
`lcg_in` is the fore-and-aft centre of gravity in inches from the middle of the
overall length (bow positive). Leave it out and the canoe floats level, as in the
designer.

The designer now shows the same seated and kneeling GM in its hydrostatics table, so
you get a stability reading while you drag sliders.

## Water profiles

`conditions.json` holds eight profiles. Each sets the speed, water depth, waves, wind,
crew posture, hard limits, and how much each result counts.

| Profile | Water | What it favours |
|---|---|---|
| `calm-lake` | Flat, deep, 4 mph | low drag, speed for the effort, enough stability, tracking |
| `fast-flatwater` | Flat, 5 mph, low seats, more power | drag and speed above all |
| `big-lake-chop` | 1 ft wind chop at 2.4 s, 10 mph headwind | dry bow, gunwale height under heel, drag into waves, tracking, low windage |
| `boat-wakes` | 1 ft short steep wakes at 1.7 s | dry bow and low pitching |
| `coastal-swell` | 2 ft swell at 7 s, salt water | reserve stability, tracking, windage |
| `shallow-river` | 2 ft deep, 3.5 mph | shallow-water drag, shallow draft, turning |
| `moving-water` | Class I-II, standing waves, kneeling | turning, dry bow, secondary stability |
| `kids-pack-boat` | Calm pond, one young child sitting low, 8 W, 2 mph | peak righting moment, gunwale angle, narrow gunwales for short arms, low sides, easy speed |

To make your own, copy a block and change it. `targets` give `[poor, good]` for a
result: the result scores 1 at good, 0 at poor, and keeps falling past poor (to −1)
so the optimizer can't trade one result away entirely. `weights` set how much each
counts, and `constraints` are hard limits `[min, max]` (use `null` for none).
Any key in a report's table can be used; the names are in `report.py` (`ROWS`).

## Optimizer options

```
python -m canoe_analysis optimize designs/mine.json -c moving-water \
    --vary beam,depth,rocker,rise,secExp,planExp,fine,angle \
    --bound rocker=2:7 --gens 40
```

`--vary` takes any designer slider name (`length`, `beam`, `depth`, `mid`, `tumble`,
`rocker`, `rise`, `sheerExp`, `angle`, `radius`, `secExp`, `planExp`, `fine`, `tlen`).
Bow and stern move together unless you pass `--unlink`, then name them `b_rocker`,
`s_rocker` and so on, which lets it find asymmetric hulls (a fuller stern, a finer
bow). Everything you don't name stays as in the starting design, so length, hull
weight and payload are fixed unless you add them.

## How much to trust it

- Hydrostatics match the designer to within 0.01 in of draft and 1 lb of capacity
  on its presets. Waterline length here is about 1% longer because the
  waterline ends are interpolated between stations.
- The Michell wave-drag code reproduces a brute-force evaluation of the classical
  integral on the Wigley test hull to within a few percent, and shows the expected shallow-water
  hump near the critical speed. Thin-ship theory exaggerates humps and hollows and
  is most reliable for long, slender hulls; it is good for ranking canoe shapes, less
  so for absolute pounds of drag. The default tandem tripper comes out at about
  4 lbf at 3.5 mph and 5 lbf at 4 mph, in the range of published canoe and touring
  kayak tow tests.
- The wave response is linear strip theory: right in trends and rankings, rough in
  absolute numbers, and it ignores roll (which depends mostly on the paddlers).
- Stability is static. Paddlers balance actively, so a narrow hull with GM near zero
  can still be paddled; treat GM limits as comfort margins, not capsize lines.
- The hull is held at its static waterline at speed (no dynamic sinkage or trim).
- The wave-drag model rewards rocker and wide, shallow sections more than real
  canoes bear out. In the sample calm-lake search it pushed beam to 37 in and rocker
  to 5 in. Hold beam with `--bound beam=lo:hi` (or leave it out of `--vary`) and cap
  rocker when you want a believable flat-water hull.

Use the numbers to compare shapes and see which way a change pushes things, and
check a shortlisted design against real-world experience before building a mold.

## Merging into the PC project

The package is self-contained (`numpy` only, plus `matplotlib` for plots). To use it
next to `hull/geometry.py` and `config/default.json`, copy the `canoe_analysis/`
folder and `conditions.json` into the project root, then for example:

```python
from canoe_analysis.config import load
from canoe_analysis.analysis import evaluate
from canoe_analysis.scoring import load_conditions, score

cfg, params = load('config/default.json')
cond = load_conditions()['big-lake-chop']
metrics = evaluate(params, cond)
print(score(metrics, cond)['score'], metrics['gm_in'], metrics['resistance_lbf'])
```

`config.save()` writes results back over an existing config, keeping any other
sections in it. If `hull/geometry.py` has changed since the designer was built,
compare it with `canoe_analysis/geometry.py`; the two should agree, and the
designer comparison in "How much to trust it" is the quick check.

## Files

- `canoe_analysis/geometry.py` hull surface, same equations as the designer
- `canoe_analysis/hydrostatics.py` upright and heeled flotation
- `canoe_analysis/stability.py` load case and righting-arm curve
- `canoe_analysis/resistance.py` friction and Michell wave drag, finite depth
- `canoe_analysis/seakeeping.py` heave, pitch, wetness and added drag in waves
- `canoe_analysis/analysis.py` runs everything for one design and condition
- `canoe_analysis/scoring.py`, `optimize.py`, `report.py`, `__main__.py`
- `conditions.json` water profiles
- `designs/` the designer's presets as settings files
- `results/` reports and optimizer runs
