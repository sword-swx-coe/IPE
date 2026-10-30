# Bit-exact checkpoint restarts in IPE

Branch `hemispheric-exb`, commits 3586f36, 8dc3251, 0162c5f, 9a3c807 (October 2026).
Contact: Naomi Maruyama (naomi.maruyama@lasp.colorado.edu).

## Summary

Before these commits, an IPE run restarted from an `IPE_State.apex.YYYYMMDDHHMM.nc`
checkpoint did not reproduce the uninterrupted run. Four independent causes were found and
removed. A cold restart is now bit-identical to the continuous run (verified on a one-step
restart and on a 6-hour warm / 3-hour cold restart, all 27 state variables, 8 MPI ranks).
Two of the causes were genuine model bugs that affected every run, restart or not.

| # | Cause | Where | Effect on normal runs | Commit |
|---|---|---|---|---|
| 1 | MSIS/HWM call skipped at the first step of a warm start (`elapsed_sec > 0` guard) | `src/ipelib/IPE_Neutrals_Class.F90` | none | 3586f36 |
| 2 | Photoelectron production frequencies kept in automatic (stack) arrays, recomputed only when F10.7 changed by 5 % | `src/ipelib/flip/RSPE2B.f` (PE2S) | **bug**: the first flux tube processed on each rank in every time step ran with garbage frequencies (zero secondary ionisation, ~10x too little photoelectron heating) | 8dc3251 |
| 3 | Cross-rank sum of the polar-ring values with `MPI_ALLREDUCE(MPI_SUM)` | `src/ipelib/IPE_Plasma_Class.F90`, `Calculate_Pole_Values` | reproducibility only (last-bit differences between a fresh and a long-running process) | 0162c5f |
| 4 | Variables flagged by `-Wmaybe-uninitialized` in FLIP (14 sites) | `src/ipelib/flip/*.f` | none measurable (bit-identical before/after) | 9a3c807 |

## How to restart exactly

1. Build from 9a3c807 or later (or cherry-pick the four commits; 8dc3251, 0162c5f and 9a3c807
   touch only FLIP and the plasma transport and apply cleanly to other branches).
2. Run the first segment; a full state is written every `FILE_OUTPUT_FREQUENCY`. Any such file
   is a valid restart point.
3. For the second segment set, in `IPE.inp`:
   - `&TIMESTEPPING`: `INITIAL_TIMESTAMP` = stamp of the checkpoint; `START_TIME` = UT seconds of
     that stamp (the driver resets the time of day to it); `END_TIME` = `START_TIME` + the length
     of the segment, an integer multiple of `FILE_OUTPUT_FREQUENCY` (the driver loops
     `(END_TIME - START_TIME)/FILE_OUTPUT_FREQUENCY` times).
   - `&FILEIO`: **`MSIS_ON_RESTART = T`** (new switch, default `F` keeps the old behaviour of
     holding the file's neutrals for the first MSIS interval). Without it the first three steps
     use 15-minute-stale neutrals. Check the log: the first `--> Calling MSIS at` line must carry
     the restart time, not 15 minutes later.
   - Forcing files (F10.7/Kp, SME) are indexed by absolute date on this branch; on branches that
     index by record, set `F107_KP_SKIP_SIZE` to the restart offset.
4. Both segments must use the same binary and the same number of MPI ranks.

The checkpoint written at the segment boundary and the one the continuous run would have
written are then identical, and so is everything after it.

## Details of the two model bugs

**PE2S production frequencies (`RSPE2B.f`).** `RJOX, RJN2, RJO2, RJHE(201)` are plain local
arrays (no SAVE). `CONVF_EUVAC` filled them only when `ABS((F107-F107SV)/F107) >= 0.05`, with
`F107SV` DATA-initialised. After the first call of a process every later call reused whatever
the previous call had left on the stack. For consecutive tubes within a step the stack region
survived, so the values were right by accident; between steps other code overwrote it, so the
first tube processed on each rank in every step ran with garbage (PEPION = 0, photoelectron
heating about ten times too low). Fix: compute the frequencies on every call (cost negligible;
this also removes the 5 % staleness).

**Pole-value reduction (`Calculate_Pole_Values`).** The `MPI_ALLREDUCE(MPI_SUM)` over the ranks'
partial sums of the polar ring was summed in an order that differed between a freshly started and
a long-running process (observed with MPICH; mechanism not pursued). Replaced by `MPI_ALLGATHER`
and an addition in rank order on every rank: same arithmetic, fixed order.

**Uninitialised variables (9a3c807).** RSPE2B: IPAS, PASK, RAVMU; RSJACA: IBW; CMINOR: H;
Rates: RATIO; RSSUBC: JS, GLATD; RSDENA_EXB: IUN; FLIPSUBS: J180K, NETHFLX, NETOFLX;
FLIPWIND: NUMCOL; FLIPAP: KDAY; FLIP_GRID: SREF. All set explicitly to the value the code relied
on implicitly, so results are unchanged. Note on RAVMU: at `Z(J) == Z(M)` the legacy code reuses
the previous point's pitch-angle factor; that behaviour is kept and left as a physics question.

## The deck must parse: namelist errors are now fatal

Until 2026-10-30 IPE read each namelist group with `IOSTAT` captured but never checked. A
malformed group aborted its READ silently and every variable listed *after* the bad token kept its
default. The usual trigger is an unquoted string, `FILE_PREFIX = IPE_State.apex.` or
`FILE_EXTENSION = .nc` (gfortran IOSTAT 5010), which many hand-written decks carry; any
`MSIS_ON_RESTART = T` placed after it was lost, and the restart was not exact although the deck
said it should be. `Build_IPE_Model_Parameters` now stops the run with

    IPE000: ERROR - IPE_Model_Parameters_Class.F90:NNN  Syntax error in namelist group &FileIO of IPE.inp (check for unquoted strings or misspelt names)

Quote every string value. A group that is absent from `IPE.inp` is still allowed (the sample
deck has no `&INDICESFILES`); Intel reports it with a note, gfortran cannot tell.

## Consequences for existing results

Every run made before 8dc3251 carries bug 2 in the first tube per rank per step (with 8 ranks,
8 flux tubes out of ~6,800 each step, mostly polar tubes). Regression baselines produced with
older binaries will differ from 9a3c807 output in those tubes and should be regenerated before
being used for bitwise comparison.

## Method used to find the causes (for the record)

Source audit of all state that persists between steps but is not in the checkpoint; a
determinism test (two identical cold restarts, bit-identical); a warm-reload experiment that
re-read a checkpoint into a running model (reproduced the continuous run, proving in-memory state
rather than nondeterminism); per-stage checksums and rank-selectable dumps inside the plasma
update and inside FLIP (CTIPINT stages) to locate the first differing operation; a two-minute
warm/cold protocol (warm 12:00-12:20 with 5-min outputs, cold restart from its 12:15 state) for
each hypothesis; `-finit-local-zero` builds and `-Wmaybe-uninitialized` scans for the last cause.
