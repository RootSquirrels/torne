# Experiments

This directory holds exploratory scripts: exploratory analyses, quick hypothesis checks, comparisons of options, small
feasibility simulations, and the scripts that run a mission against the network.

What does not belong here:

- anything meant to become production code — that belongs in `src/torne/`, with its tests;
- data and secrets, which stay out of the repository and are referenced only by their provenance;
- results presented as established without going through the validation record.

Rule of passage: **an experiment becomes code only if it survives review** — another person can read it, understand
it, reproduce it and see its value. What fails that test stays here, or disappears.

## What is here today

| Script | What it does | Network |
|---|---|---|
| `acquisition_demo.py` | Acquisition socle demonstration. | yes |
| `mission_001_demo.py` | The whole chain on synthetic data: acquisition, execution, evaluation, record. | no |
| `mission_002_real_world.py` | The same chain **on the real world**: 33 481 daily values of the Mississippi at Grafton (USGS-05587450, 1933→2026) from the OGC API, read as observations, day-of-year climatology compared with the agency's published statistics, standardised anomaly index, and a knowledge product with verified lineage. | yes; `USGS_API_KEY` beyond the anonymous quota |
| `mission_003_hydro001.py` | **HYDRO-001**, source qualification: bounded acquisition of the two Hub'EAU feeds (stage `H`, discharge `Q`), station selection by declared criteria, and an out-of-sample, chronological evaluation of whether the published discharge is a function of the published stage. Protocol: [`docs/PRE-REGISTRATION-HYDRO-001.md`](../docs/PRE-REGISTRATION-HYDRO-001.md). | yes; no key |
| `atmo_001_sources_probe.py` | ATMO-001 accessibility inventory of 17 atmospheric access points. | yes |
| `atmo_001_premiere_acquisition.py` | ATMO-001 acquisition of four GHCN-Daily French stations and their exploratory profile. | yes |
| `atmo_001_meteofrance.py` | ATMO-001 Météo-France route, as it answers with or without a token. | yes; `METEOFRANCE_TOKEN` |

Scripts that touch the network write their raw evidence to a temporary directory they print at the end. Keys and
tokens are read at the last moment and never appear in a recorded request. Hub'EAU throttles (`503` when asked too
fast); `mission_003_hydro001.py` rides it out with the socle's widened retry policy and says so if it stops on its
budget.

The `atmo_001_*` scripts predate the English rule and still carry French identifiers and messages; they are translated
when next touched (`docs/PROGRAMME.md` §6).
