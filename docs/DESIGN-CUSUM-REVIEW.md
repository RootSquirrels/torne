# CUSUM in `methods/` - design review (not implemented)

> **Status: approved with changes, then implemented in `methods/breaks.py`** (`cusum_hac_sensitivity`,
> `cusum_block_bootstrap`). Decisions applied: `bartlett_lags`, `cusum_break_test` and `BreakResult`
> are unchanged; the HAC route is an extra sensitivity table, not a replacement; no synthesized
> maximum p-value in any native result (a worst-case summary is for experiments to compute); the
> bootstrap is a **non-circular** moving block bootstrap, every source block inside one contiguous
> observed run, an explicit `step` is required with `positions`, the original layout of runs is
> reproduced, and an unsupported block length raises; both routes live in `breaks.py`; the null
> procedure and the HAC-studentized vs bootstrap-calibrated distinction are documented in the code.
> Serialization audit: `BreakResult` is not serialized or fingerprinted anywhere; its consumers read
> fields (`RegimeChangeReport` copies them, `atmosphere/profile.py` returns it, experiments print or
> rebuild dicts field by field). The new routes use their own result types.
>
> **Measured on synthetic series (300 replications each, 5 % nominal, `scratchpad` script, not a test
> threshold):** iid n=200: bootstrap b=4 rejects 0.05, existing HAC default 0.03. AR(1) n=600:
> phi=0.5 -> bootstrap b=15 0.07, b=40 0.04, HAC default 0.09; phi=0.8 -> bootstrap b=15 **0.13**,
> b=40 0.05, HAC default **0.26**. Reading: the existing default window over-rejects on a persistent
> series, and the bootstrap is only calibrated when the block is long enough for the dependence:
> its block-length grid must be read, not collapsed. Power for a 1-sd mean shift (n=200): 1.00.

## 1. What exists today [FACT]

`methods/breaks.py`: `cusum_break_test(xs, *, lags=0)` computes `max|S_k| / (sigma_lr * sqrt(n))`
with a Bartlett-kernel long-run variance and a Kolmogorov survival function. `lags=None` means
`bartlett_lags(n) = floor(4 (n/100)^(2/9))`; `lags=0` means plain variance.

**Callers that a change could move:**

| Caller | Uses | Effect of changing `bartlett_lags` or `lags=None` |
|---|---|---|
| `evaluation/uncertainty.py` | `bartlett_lags(n)` for a Newey-West variance | changes evaluation intervals |
| `methods/compare.py` (`detect_regime_change`, line ~143, ~257) | `bartlett_lags`, `cusum_break_test(lags=None)` | changes regime-change reports |
| `atmosphere/profile.py` | `cusum_break_test(lags=None)` | changes ATMO profile numbers |
| `experiments/mission_003_hydro001.py` | `cusum_break_test(debits)` (default `lags=0`) | HYDRO product; unaffected unless the default changes |
| `tests/test_statistical_methods.py` | pins `bartlett_lags(100) == 4`, `(16) == 2` | breaks if the rule changes |

**Rule consequence:** `bartlett_lags` and the default of `lags` must **not** change. New behaviour
is opt-in.

## 2. What ATMO-002 measured [FACT]

On four GHCN-Daily series of ~30 000 daily anomalies (`docs/ATMO-002.md`, section 3.4):
`bartlett_lags` gives 14 lags while the autocorrelation is still far from zero; p-values move from
1e-57 (14 lags) to 5e-11 (365 lags) at Lille, and a circular block bootstrap gives p <= 0.002 at
every block length tried. Removing a linear trend changes the conclusion at some stations
(Paris: p 0.49). So the window choice, the dependence treatment and the trend all matter, and
none is a property of "CUSUM" itself.

## 3. Proposal: two routes, kept apart

The statistic `max|S_k|/sqrt(n)` is shared; what differs is **how its null distribution is
obtained**. The two routes are separate functions with separate result types, so a caller cannot
mix them or take the better p-value.

**Route A - HAC long-run variance (existing, made explicit).** Keep `cusum_break_test`. Add a
documented `long_run_variance_sensitivity(xs, lags_grid)` that returns the statistic and p-value
**for each window in a caller-supplied grid** and the autocorrelation at those lags. There is no
automatic window selection: an automatic rule can read trend or seasonality as long memory and give
a false impression of correction. The docstring states the assumption (stationarity of the mean
under H0, short-range dependence relative to the window).

**Route B - block-bootstrap inference.** New `cusum_block_bootstrap(xs, *, block_lengths,
n_bootstrap, seed, positions=None)`. The caller supplies a **grid** of block lengths; the result
reports the observed statistic, the null 95 % quantile and the p-value **at every block length**,
plus the p-value resolution `1/(n_bootstrap+1)`. There is no "best" block length and no headline
p-value chosen by the function; if a summary is wanted it is the **maximum** p across the grid
(the least favourable), stated as such. The null is a circular block bootstrap of the centred
series; with `positions`, blocks are built on real positions, not on the compressed index.

**Trend and non-stationarity are not handled by either route.** A `detrend` option would be a
modelling decision (linear? seasonal?) that belongs to the domain. The functions test a constant
mean and say so; the domain decides what to remove before calling, and reports both versions as
ATMO-002 does.

## 4. Dependencies between the three corrections

1. `sample_autocorrelation` with positions (done) - the primitive.
2. `effective_sample_size_diagnostics` (done) - uses it.
3. CUSUM: Route A's reported autocorrelations and Route B's gap-aware blocks use it. Route B should
   not be written before the block construction on `positions` is settled.

## 5. Tests (all offline, seeded)

- Regular series, no break, iid and AR(1): size of the bootstrap test near nominal over repeated
  seeds; Route A unchanged versus the existing tests.
- A known mean shift of a stated size: both routes reject; power reported, not assumed.
- A pure linear trend with no step: both routes reject a constant mean (documented behaviour); the
  detrended series does not.
- Gaps: a series with a long gap versus the same series compressed: block bootstrap on `positions`
  does not splice across the gap.
- Sensitivity grids: results are returned for every window / block length, never reduced silently.
- Determinism: same seed, same output; global random state untouched (as in `test_dependence.py`).

## 6. Questions for the reviewer

1. Is "maximum p across the grid" an acceptable optional summary, or should the API return the
   table only?
2. Route B with `positions`: circular wrap-around across a long gap is wrong for non-stationary
   gaps. Accept block starts restricted to blocks fully inside observed runs?
3. Should Route A and B live in `breaks.py` or in a new `methods/inference_breaks.py`? (The first
   keeps one module per statistic; the second keeps `breaks.py` free of resampling.)
4. Persisted formats: the new result types are new classes, no existing class changes. Confirm that
   nothing persists `BreakResult` field-by-field in a way that a *new sibling* type could confuse.
