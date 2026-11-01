# TORNE — Pre-registration HYDRO-001

**Status**: fixed before any evaluation result was read.
**Written**: 2026-11-01, before the first run of `experiments/mission_003_hydro001.py`.
**Protocol implemented by**: `experiments/mission_003_hydro001.py`.
**Question answered by the published product**: `torne.hydro-001.hubeau.<station>.relation`.

This document is the contract between the experiment and whoever reads its
result. Everything that could be decided by looking at the outcome is decided
here, in advance, and the script follows this document rather than the other
way round.

---

## A. Identity and governance

### A.1 Identifiers

| | |
|---|---|
| Milestone | HYDRO-001 — first end-to-end knowledge product on a real physical system |
| Source | Hub'Eau v2, `hydrometrie/observations_tr` (`hubeau.hydrometrie.observations_tr`) |
| Object | one hydrometric station of the French network, and the relation between the height it publishes and the discharge it publishes |
| Method | `torne.hydrology.rating_curve` v1.0.0 |
| Protocol | `experiments/mission_003_hydro001.py` |
| Randomness | none. The fit is a least squares, the bootstrap uses a fixed seed |

### A.2 What motivates this experiment

The source publishes, for every observation, the **method** the agency used to
obtain it. On this access point, the height rows carry the method `Mesurée`
(measured) and the discharge rows carry the method `Calculée` (computed): the
agency states that the discharge it publishes is *derived* from the height it
publishes.

That statement is a claim about the **data-generating process** of the
source, and it is checkable. If it holds, the published discharge carries no
information that the published height does not already carry — which is a
first-order fact for anyone who treats a discharge observation and a height
observation as two independent measurements. If it does not hold, the agency's
method flag is not a description of what it is used to describe.

The experiment is deliberately narrow: one station, one relation, one
chronological split, one decision rule.

### A.3 Conditions of the freeze

This document was written **before** the evaluation of the relation was run.
The quantities that were known when it was written — the behaviour of the
access point, the shape of the rows, the fact that the discharge rows carry
two declared methods — are recorded in `docs/SOURCES.md` §1 and in the
exploration notes of the mission.

The quantities that were **not** known, and that this document fixes in
advance, are: the station that will be selected, the number of instants it
will carry, the shape of the relation, and its out-of-sample error.

### A.4 Owner

The milestone's owner asks for one defensible piece of knowledge about a real
physical system. A negative or inconclusive result is an acceptable outcome
and is published as such.

---

## B. Question and hypothesis

### B.1 Research question

> **Q1.** At the station selected by the criteria of §C.3, is the discharge
> published by the agency a deterministic function of the height it publishes?
> In particular: does a relation fitted on the **earlier** part of the record
> reproduce the discharge published for the **later** part, better than the
> trivial baseline ("the discharge did not change")?

### B.2 The claim, and what it is not

The claim is about the **relation between two published numbers** at one
station, and about how well the relation transfers to a period it was not
fitted on.

It is **not**:

- a claim about the absolute correctness of the published discharge — the
  experiment never compares the discharge with an independent measurement;
- a claim about the state of the river — a relation between two published
  numbers says nothing about the water itself;
- a claim about a forecast — the relation is applied to the height *at the
  same instant* as the discharge it reproduces. It is a retrospective
  reproduction, and it is called one throughout;
- a claim about a causal mechanism — no mechanism is identified here.

### B.3 Main hypothesis

**H1.** The relation fitted on the training window reproduces the discharge
published for the test window with a **relative error below 5%** of the mean
published discharge, and beats the **persistence** baseline (the discharge did
not change) by a factor of at least **2**.

### B.4 Null hypothesis — pre-registered as a valid result

**H0.** The relation does not reproduce the published discharge out of sample:
either its relative error exceeds 5%, or it is not better than persistence.
**A negative or inconclusive result is a valid scientific outcome and will be
published as such.**

### B.5 Alternative hypotheses and the results that would refute H1

| Refutation | Formulation |
|---|---|
| **R1 — the method flag does not describe the relation** | The published discharge is not a function of the published height (the out-of-sample error is large, or the relation is worse than persistence). The agency's `Calculée` flag would then not describe what it is used to describe. |
| **R2 — the relation does not transfer** | The relation reproduces the training window and fails on the test window (the error grows sharply at the end of the record). The agency would then be revising the relation as it goes. |
| **R3 — insufficient power** | The test window is too short, or the discharge barely moves, for the comparison to say anything. → **inconclusive**, which remains a valid result. |
| **R4 — the baseline is not trivial** | The persistence baseline is as good as the relation (the discharge is nearly constant over the window). The relation would then be *correct but useless*, and the honest verdict is inconclusive on the question asked. |

### B.6 Prior art

None within TORNE: this is the first knowledge product of the platform built
on this source. The related work in the repository is the USGS OGC mission
(`experiments/mission_002_real_world.py`), which uses a different source, a
different variable and a different question.

---

## C. Data and temporality

### C.1 Source

| | |
|---|---|
| Identifier | `hubeau.hydrometrie.observations_tr` |
| Access point | `https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr` |
| What is asked for | the **height feed** (`grandeur_hydro=H`) and the **discharge feed** (`grandeur_hydro=Q`), each without a station filter and without a time window |
| Why no filter | measured on 2026-11-01: this access point **echoes but does not apply** `code_station`, `code_cours_eau`, `date_debut` and `date_fin`. Asking for a station would be asking a question the source does not answer, and the conformity gate would (rightly) close. The selection of a station is therefore a **declared and verified transformation** of the acquired evidence (`torne.hydrology.hubeau`), never a filter the provider is trusted to apply. |
| Conformity criterion | the only one the source can satisfy: the rows that come back carry the quantity that was asked for. It is verified **on the rows**, not on the request. |

### C.2 Acquisition budget

| | |
|---|---|
| Page size | 2 000 rows (the instance accepts up to 10 000 and answers 503 when pushed) |
| Depth | 40 pages per feed, i.e. at most 80 000 rows per feed |
| Patience | the socle's retry policy, widened: 6 attempts, 5 s → 120 s |
| Raw evidence | every page is kept, addressed by its fingerprint, in a temporary directory the run prints |
| Truncation | the walk may stop on the budget before the source is exhausted; the socle records it, and the product says so |

### C.3 Selection of the station — criteria fixed in advance

A station is eligible when **all** of the following hold. They are read on the
metadata and on the completeness of the record, and never on the values the
station published.

| Criterion | Value | Why |
|---|---|---|
| Paired instants | ≥ 16 | the experiment needs a training window and a test window; the number is set by what the protocol needs, not by what a station offers |
| Completeness | ≥ 90% of the instants expected at the modal sampling interval | a station that is there only half the time cannot support a relation |
| Vertical datum | a single one | the relation compares heights; two datums are two heights |
| Coordinates | present | the station must be located, not anonymous |
| Missing values | none | a relation fitted across a hole is a relation about an interpolation |
| Measurement status | a single one | the quality of the record must be uniform |

**Tie-break**: the station with the longest paired record, then the
lexicographically smallest station code. Both are properties of the *record*,
not of its values, and the tie-break is deterministic.

### C.4 Temporal semantics

The rows carry the instant of the observation (`date_obs`, UTC). The source
publishes **no** publication instant; the publication is therefore declared
**bounded** below by the instant of the observation, which is a fact (a value
cannot be published before it is observed) and not an assumption about the
publication lag.

### C.5 What is preserved, and what is refused

Preserved: the raw pages, verbatim, under the source's own field names; the
station identity, the site, the coordinates, the vertical datum; the method,
the qualification, the status and the continuity, under their own names; the
missing values, as missing.

Refused: a row without a station code (it cannot be attributed to a station,
and no station is invented for it); a value that is not a number.

The unit of the **height** is not published by the source. It is carried as
`not declared by the source`, and no dimensional claim about a height is made
anywhere in this experiment.

---

## D. Method

### D.1 The relation — fixed in advance

The relation is fitted in the logarithms:

```
log Q = a + b · log H
```

which is the power law a rating curve is, written so that the fit is a
straight line. The fit is an ordinary least squares
(`torne.methods.regression.ols`) — **no new mathematical primitive is
introduced**.

Fixed in advance:

- the functional form (log-linear, **no** datum offset `h0` is fitted);
- the estimation window (the training window of §E.1);
- no weighting, no robust loss, no cross-validation: one fit, one window.

### D.2 The model in the platform

`torne.hydrology.rating_curve` v1.0.0, nature `ESTIMATED`. It reads the two
aligned series `stage` and `discharge` and returns the discharge the relation
assigns to each stage.

### D.3 The baselines — fixed in advance

The socle computes three, on the same split, fitted on the same training
window: **persistence** (the discharge did not change), **mean** (the training
mean) and **drift** (the training trend).

### D.4 The metrics — fixed in advance

`rmse`, `mae` and `bias` (`torne.evaluation.metrics`), computed on the test
window only.

---

## E. Evaluation

### E.1 The split — fixed in advance

The paired instants are ordered chronologically. The **first two thirds** form
the training window; the **last third** forms the test window. The split is
recorded in the evaluation report with its indices, and is therefore
replayable.

The test window is evaluated **in one block**: the relation fitted on the
training window is applied to every instant of the test window.

### E.2 The leakage verification — fixed in advance

| Rule | How it is enforced |
|---|---|
| The fit never sees a test discharge | the predictor receives the training block only |
| The test window is strictly later | the split is chronological, and the indices are in the report |
| The publication instant of an observation is never used as an input | the relation reads the measurement, not the publication |
| No future observation can reach a past estimate | the training block of a fold is a prefix of the series |

The rule is structural, not a promise: the predictor's signature receives the
training block, and the socle's walk-forward does the rest.

### E.3 The uncertainty — fixed in advance

- The **95% interval** on the mean squared error, with the long-run variance
  (Newey–West) of the loss series (`torne.evaluation.uncertainty`).
- The **Diebold–Mariano** test of the loss difference between the relation
  and the persistence baseline, one-sided in favour of the relation
  (`torne.methods.calibration`).
- The **bootstrap** of the relative error over the test window
  (`torne.methods.dependence`), with a fixed seed.

### E.4 The reference — fixed in advance

The reference is the **agency's own published discharge**: an independent
publication by the producer, of the quantity the relation is supposed to
reproduce. It is not a third-party reference, and the product says so.

---

## F. The decision rule — fixed in advance

| Verdict | Condition |
|---|---|
| **SUPPORTED** | the relative reproduction error is **≤ 5%** of the mean published discharge, **and** the relation is at least **2×** better than persistence (rmse), **and** the Diebold–Mariano test rejects the equality of the losses at the 5% level, in favour of the relation |
| **CONTRADICTED** | the relation's rmse is **greater** than the persistence baseline's rmse on the test window |
| **INCONCLUSIVE** | everything else |

The three conditions of SUPPORTED are conjunctive: a relation that is accurate
but not better than a trivial baseline does not support H1 (refutation R4), and
a relation that beats the baseline without being accurate does not either.

---

## G. What this pre-registration does not claim

- It does not claim the published discharge is **correct**. It claims it is
  **reproducible** from the published height.
- It does not claim the relation holds outside the acquired window. The domain
  of validity of the published product is the training window.
- It does not claim the height's unit. The source does not publish it.
- It does not claim a mechanism. If the relation holds, the mechanism is the
  agency's rating curve, and this experiment does not test the rating curve
  itself, nor the agency, nor the river.
- It does not claim a generalisation to the whole network. One station is one
  station; the network's own behaviour is reported as a fact of the acquired
  evidence, and is not the object of the verdict.

---

## H. What happens if the run cannot follow this protocol

If the acquisition is truncated by the throttle, or if the selected station
carries fewer paired instants than §C.3 requires, the run **stops and says
so**; it does not lower the criteria to obtain a result. A run that cannot
follow the protocol publishes no product.
