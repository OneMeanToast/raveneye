# Event taxonomy

The 11 `EventType` values are the building blocks of the demand layer. Each
one is a **doctrinally grounded** category of world-state change that a
collection manager would expect to see flowing across a watch floor in a
maritime-interdiction scenario. Stakeholders react to these events through
their per-type utility weights (see `docs/bidding_interface.md`).

For each type below: definition, doctrinal analog, typical severity range,
typical LTIOV (latest time the information is of value), and an example
narrative line in the spirit of what the scenario emits.

> Citations are illustrative pointers into open Army / joint doctrine. They
> are not endorsements; the sim is unclassified and uses public terminology.

---

## KINETIC_STRIKE

A munition impact (or credible report of one) against a vessel, facility, or
fixed site. High-stakes; almost always triggers a BDA collection requirement
and a force-protection response.

- **Doctrinal analog:** FM 3-60 (Targeting); JP 3-60. BDA trigger; battle
  damage assessment is the canonical follow-on collection task.
- **Severity:** 4–5
- **Source confidence:** 0.85–0.99 (kinetic events tend to be reported with
  high confidence)
- **LTIOV:** 2–8 hours (BDA degrades fast)
- **Example:** *"Container ship hit by projectile in Gulf of Oman approach;
  BDA requested."*

## MINE_LAYING_REPORT

Mine-emplacement activity in or near a navigable choke point. Time-critical
because subsequent shipping is at risk until MCM coverage clears the area.

- **Doctrinal analog:** JP 3-15 (Barriers, Obstacles, and Mine Warfare).
  Immediate area-denial threat; MCM tasking priority.
- **Severity:** 4–5
- **Source confidence:** 0.55–0.80
- **LTIOV:** 2–6 hours
- **Example:** *"IRGC minelayer activity reported in TSS lane overnight; MCM
  cueing required."*

## NAVAL_POSTURE_CHANGE

Change in surface-combatant disposition, tempo, or readiness state — fast
boats sortieing, AOR repositioning, port-out signatures.

- **Doctrinal analog:** FM 34-2 (Collection Management) — indicators-and-
  warning tripwire.
- **Severity:** 3–5
- **Source confidence:** 0.65–0.90
- **LTIOV:** 6–18 hours
- **Example:** *"IRGCN fast-boat surge from Bandar Abbas; force-protection
  posture under review."*

## MOVEMENT_DETECTED

Ground or maritime movement consistent with adversary TTP — vehicle convoys,
launcher dispersal, unscheduled departures.

- **Doctrinal analog:** ATP 2-01 (Plan Requirements and Assess Collection)
  pattern-activity / I&W cueing.
- **Severity:** 2–4
- **Source confidence:** 0.55–0.90
- **LTIOV:** 4–14 hours
- **Example:** *"6+ vehicles departing Qeshm garrison; possible coastal-
  defense launcher dispersal."*

## VESSEL_DARK

A vessel of interest disables AIS in or near a watched corridor. Often the
opening move of a blockade-running attempt.

- **Doctrinal analog:** Maritime pattern-of-life anomaly cueing — used as
  trigger for further imaging and pattern analysis.
- **Severity:** 2–4
- **Source confidence:** 0.60–0.90
- **LTIOV:** 4–12 hours
- **Example:** *"VLCC turned off AIS near Larak; track lost; reacquire
  request issued."*

## BLOCKADE_RUNNER

A specific vessel actively attempting to transit a declared interdiction
zone. Distinct from `VESSEL_DARK` — this is the act, not the cue.

- **Doctrinal analog:** Maritime interdiction operations (MIO) cue;
  intercept-vector planning.
- **Severity:** 3–5
- **Source confidence:** 0.70–0.92
- **LTIOV:** 3–10 hours
- **Example:** *"Dark VLCC loading at Kharg; departure imminent under
  fraudulent flag."*

## HUMINT_REPORT

Human-source-derived report. Lower confidence by default; corroboration
loops are usually what generate follow-on imaging tasks.

- **Doctrinal analog:** ATP 2-22.3 (Human Intelligence Collector
  Operations). Confidence handling is doctrinal.
- **Severity:** 2–4
- **Source confidence:** 0.35–0.70
- **LTIOV:** 12–48 hours (usually slower-burning than collection cues)
- **Example:** *"Source reporting tanker-truck convoy near Bandar Mahshahr;
  possible fuel diversion."*

## SIGINT_CUE

Emitter activity or C2 pattern change consistent with tasking-worthy
events — a radar coming up, a circuit changing key, a unit-level handoff.

- **Doctrinal analog:** ATP 2-22.5 (SIGINT) trigger / cue products.
- **Severity:** 2–4
- **Source confidence:** 0.55–0.85
- **LTIOV:** 6–18 hours
- **Example:** *"C2 emitter pattern change at Bandar-e Jask consistent with
  pre-tasking activity."*

## WEATHER_DEGRADATION

A forecast window in which EO collection is degraded — dust, haze, fog,
cloud. Not a tasking *requirement* per se, but it forces re-prioritization
and may move SAR up the queue.

- **Doctrinal analog:** ATP 2-01.3 (Intelligence Preparation of the
  Battlespace) step 4: weather effects on operations.
- **Severity:** 1–3
- **Source confidence:** 0.85–0.98 (weather forecasting is well-bounded)
- **LTIOV:** 4–18 hours
- **Example:** *"Dust/haze forecast over Strait of Hormuz; EO viability
  degraded for next 14h."*

## DIPLOMATIC_STATUS_CHANGE

A declared policy change that alters collection priorities — ceasefire
declaration, blockade reaffirmation, sanctions adjustment, port-status
change.

- **Doctrinal analog:** Commander's Critical Information Requirements
  (CCIRs) shift; FM 6-0 — these are the signals that re-task the whole
  apparatus.
- **Severity:** 3–5
- **Source confidence:** 0.90–0.99 (declared policies are unambiguous)
- **LTIOV:** 24–72 hours
- **Example:** *"CENTCOM reaffirms blockade of Hormuz; commercial transit
  prohibited until further notice."*

## FACILITY_ANOMALY

Observed deviation at a fixed site — thermal signature, flaring change,
vehicle counts, construction activity. Lower urgency than kinetic events
but the bread-and-butter of pattern analysis.

- **Doctrinal analog:** Pattern-of-life anomaly cueing for fixed
  installations.
- **Severity:** 2–4
- **Source confidence:** 0.60–0.90
- **LTIOV:** 12–36 hours
- **Example:** *"Thermal ramp at Kharg Terminal consistent with VLCC
  loading evolution."*

---

## How types map to ObservableKind

`ObservableKind` is the *thing* being observed; `EventType` is *what
happened to it*. The viewer renders both: the location's marker tells you
the kind, the dot's color tells you severity, the glyph tells you type.

| ObservableKind | Typical event types |
|---|---|
| `VESSEL` | VESSEL_DARK, BLOCKADE_RUNNER, MOVEMENT_DETECTED, KINETIC_STRIKE |
| `PORT_FACILITY` | KINETIC_STRIKE, FACILITY_ANOMALY, MOVEMENT_DETECTED |
| `REFINERY` | KINETIC_STRIKE, FACILITY_ANOMALY, BLOCKADE_RUNNER |
| `MILITARY_BASE` | NAVAL_POSTURE_CHANGE, MOVEMENT_DETECTED, KINETIC_STRIKE, SIGINT_CUE, HUMINT_REPORT |
| `ROUTE_SEGMENT` | MOVEMENT_DETECTED |
| `WIDE_AREA` | MINE_LAYING_REPORT, KINETIC_STRIKE, WEATHER_DEGRADATION, DIPLOMATIC_STATUS_CHANGE, VESSEL_DARK, HUMINT_REPORT |
| `AIRFIELD` | (reserved — not used in the v0.1 Hormuz scenario) |

The full plausibility table lives in `raveneye/sim/stochastic.py:
PLAUSIBLE_LOCATIONS`. A mine doesn't fire at Ras Tanura because the
plausibility table says it can't.

## Sensor requirements per ObservableKind

Each `ObservableKind` advertises a coarse sensor requirement that downstream
mechanism logic (v0.2) will use to gate which satellites can satisfy a bid.

| Kind | GSD (m) | Band | Revisit (h) |
|---|---|---|---|
| VESSEL | 0.5 | EO_PAN | 6 |
| PORT_FACILITY | 0.5 | EO_MS | 12 |
| REFINERY | 1.0 | EO_MS+TIR | 12 |
| MILITARY_BASE | 0.3 | EO_PAN | 8 |
| ROUTE_SEGMENT | 1.0 | EO_MS | 4 |
| WIDE_AREA | 3.0 | SAR_X | 6 |
| AIRFIELD | 0.5 | EO_PAN | 8 |

Source: `raveneye/sim/locations.py: SENSOR_REQUIREMENTS`. Tuned to be
plausible against published vendor specs (BlackSky, Planet, Capella, ICEYE,
Maxar) — see `docs/orbital_model.md` in v0.2 for vendor-by-vendor citations.

## Severity scale

Severity is integer 1–5 across all event types. The scale is
intentionally informal:

| Severity | Meaning |
|---|---|
| 1 | Background / nuisance — informs pattern analysis. |
| 2 | Routine — worth logging, may task low-priority collection. |
| 3 | Notable — single bid likely; competes for windows. |
| 4 | High — cross-stakeholder interest; deadline matters. |
| 5 | Critical — strike, mining, declared closure; force-protection class. |

The sim does not attempt to map severity to MIL-STD reporting categories
(e.g. CRITIC, FLASH); that mapping is downstream of the evaluation layer.

## LTIOV interpretation

LTIOV (Latest Time the Information is Of Value) is a duration in hours
**from the event's occurrence**. Past LTIOV, collection on the bid loses
its operational utility. The mechanism layer (v0.2) drops bids whose
matched windows end after `event.t + ltiov_hours`.

The urgency factor in `bids.derive_bids` rewards short LTIOVs:

| LTIOV | Urgency factor |
|---|---|
| ≤ 4h | 1.6 |
| ≤ 12h | 1.2 |
| ≤ 24h | 1.0 |
| ≤ 48h | 0.85 |
| > 48h | 0.7 |

So a sev-4 KINETIC_STRIKE with a 4-hour LTIOV scores 1.6× higher per
stakeholder than the same event with a 24-hour LTIOV.
