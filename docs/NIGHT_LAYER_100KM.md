# Spurious night-side E-region layer at the 100 km node (fixed)

Origin: found 2026-10-26; report, figures, check script and patch in the repository
`IPE-100km-night-layer`. Applied to `hemispheric-exb` on 2026-10-28.

## Symptom

In every IPE version since b19f807 (2020, "full convection at 200 km, zero at 100 km and
below"), the grid node at exactly 100 km on each flux tube keeps full ExB convection while the
nodes above ramp it down and the nodes below have none. On the night side this leaves a
one-node layer at 100 km where Ne exceeds the value 5 km above by a factor of several
(O2+-dominated, freshly ionised composition), inside the Pedersen conductivity peak.

## Cause and fix

`src/ipelib/IPE_Plasma_Class.F90`, `Cross_Flux_Tube_Transport`: the blend between transported
and local plasma tested `z > 100` (ramp) and `z < 100` (no transport), so z = 100.0 fell
through both and received the fully transported values. Every IPE grid built with the standard
foot spacing has nodes at exactly 90, 92, ..., 100, 102 km from each foot (verified for the
`IPE_Grid.nc` used here: 338 nodes at exactly 100.000 km, two per tube on 169 of 170 tubes).

Fix: `z.gt.100.0` -> `z.ge.100.0`. The node then takes the ramp branch with `z_factor = 0`,
identical to the below-100 km branch.

## Verification on this branch (Nov 2021 run, EXB_HEMISPHERIC = 0, quiet day 2021-11-01 00 UT)

Criterion as in the upstream report, Ne(100 km node) / Ne(node nearest 105 km) > 3, on the
native grid, 27,040 columns (tube x longitude x hemisphere):

| Columns | unfixed 9a3c807, 00 UT (restart state) | unfixed 9a3c807, 01 UT | fixed ba85e41, 01 UT |
|---|---|---|---|
| all | 4.5 % | 3.2 % | 0.0 % |
| night (LT 17-07) | 7.8 % | 5.4 % | 0.0 % (max ratio 1.1) |
| night, mlat 30-60 | 45.0 % | 33.1 % (flagged median Ne 3.0e10 m-3) | 0.0 % |
| night, mlat 60-90 | 13.6 % | 6.9 % | 0.0 % |
| day | 0.1 % | 0.4 % | 0.0 % |

One-hour runs from the same 2021-11-01 00:00 checkpoint (8 ranks, 300 s step, 12 steps). Effect
of the fix on the rest of the state after one hour (fixed vs unfixed): Ne at 250-400 km median
relative change 0.40 % (p95 8 %, max 69 % at isolated points), Ti median 0.008 K, Te median 0.19 K
(max 118 K); Ne at 95-110 km median 0.000 % (the change is confined to the one node). Check
script (native-grid criterion above): `check_night_layer_100km.py`, available from the author.

## Consequences

- Height-integrated Pedersen and Hall conductances computed from IPE plasma (the quantity
  passed to a magnetosphere model in the SWMF coupling) were too large on the night side at
  |mlat| 30-60 by a factor that depends on the local drift. Daytime values are not visibly
  affected.
- The fix changes the prognostic state in every run; results are not bit-for-bit comparable
  with pre-fix output and baselines must be regenerated (see also `RESTART_EXACTNESS.md`).
  The upstream one-hour test from the 2013-03-16 state: NmF2 median change 0.13 %, TEC median
  0.13 %, ExB drift at 300 km median 0.4 m/s.
