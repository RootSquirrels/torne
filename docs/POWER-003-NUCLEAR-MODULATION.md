# POWER-003 - French nuclear modulation, daily series

**Result: PRODUCT_VIABLE under the pre-declared protocol.** A first computed Knowledge Product: a daily series, 1 Nov 2025 - 31 Oct 2026, in `data/power-003/nuclear_modulation_daily.csv` (columns `date_utc`, `modulation_gwh`, `negative_price_hours`).

## The five conditions

| Condition | Status |
|---|---|
| Defined target quantity | Energy (GWh/day) that running reactors could have delivered at their declared available power and did not (modulation / load-following). |
| Accessible data | ENTSO-E A73 actual output per unit (57 units, 15 min, free token), EDF REMIT declarations (open), Energy-Charts prices (CC BY 4.0). |
| Executable method | `experiments/power_003_nuclear_modulation.py`, reuses the POWER-002 loaders (`power_002_declared_vs_realised.py`). |
| Independent reference | The market response: negative day-ahead price hours, and the known weekend pattern. Not an official modulation figure (none is published). |
| Economic use | Flexibility actually used by the nuclear fleet, a driver and an indicator of low and negative prices. |

## Definition

Slot (unit, 15 min): the unit is running if output >= 0.2 x Pmax. Its modulation is max(declared available power - output, 0), zero otherwise. Declared available power = Pmax minus the largest loss declared by an Active, latest-version REMIT record (records with a maximum power of 0 ignored). Daily value = sum of slots x 0.25 h, in GWh, UTC days.

## Protocol (fixed before computing) and result

| Check | Rule | Result |
|---|---|---|
| (a) coverage | >= 95 % of days | 365 of 365 days |
| (b) Spearman with negative-price hours | >= 0.5 | **+0.64** |
| (c) weekend higher than weekdays | one-sided Mann-Whitney p < 0.01 | weekend median 79.1 GWh, weekday 53.6 GWh, p < 0.0001 |
| (d) robustness, running threshold 0.3 Pmax | correlation >= 0.4 | +0.55 |

Total over the year: 22.5 TWh. Median day 58 GWh. Monthly totals between 0.6 TWh (January 2026) and 2.6 TWh (April-June 2026).

## Limits

- End-of-cycle power coast-down (stretch-out) and undeclared fuel-saving reductions are counted as modulation. The price check cannot separate them. The yearly total is therefore an upper bound of market-driven modulation.
- No official modulation figure was used to validate the level: the 22.5 TWh total is not compared with any published estimate. That comparison is the first thing to do before quoting the number.
- One year only; UTC days; the consolidated REMIT history is used (no vintage logic), which is fine for a measurement but not for a real-time use.
- The POWER-002 caveats on REMIT (rescheduled identifiers, possible gaps in the most recent weeks) apply to the declared power; here they only reduce the available power, so the modulation is if anything understated for badly declared units.

## Not done

- No forecast of modulation (this is a measurement). A forecast from day-ahead prices and weather would be the next step.
- No comparison with an official or EDF-published volume.
- Only one year was computed; the A73 history allows an earlier start.
