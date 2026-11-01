# TORNE — Research and validation

**Doctrine of evidence**
**Status: applicable principles.** The repository contains models, their execution, their evaluation and a
replayable record; it contains **no established scientific result**. The distinction is sharp: this document says
how a claim must be tested, and the repository does not yet claim to have demonstrated anything about the real
world.

## 1. Principle

Evidence is proportionate to the claim. No validation mode is universally superior, and no single method proves
everything.

Knowledge built on the past can be tested on later historical events. That approach is legitimate provided that
periods, data, choices and available information are cleanly separated.

Every claim must therefore be stated before it is tested: what is claimed, on which domain, over which period, with
which data, compared with what, and with which success and failure criteria.

### 1.1 Novelty is itself a claim to test

TORNE's purpose is to produce information that is absent from its inputs. "This is new" is therefore a claim with
its own evidence requirement, not a description:

- the quantity produced is **published by none of the inputs**, nor a re-expression of one of them (an anomaly
  against a source's own climatology re-expresses that source);
- on withheld data, the multi-source result **does better than every single-source baseline** on the same target —
  the ablation "one data family at a time";
- the families compared in the ablation are **independent**, which is read from a dependence ledger before the
  ablation is interpreted (`src/torne/eo/coverage.py`); a product computed from the same meteorological inputs as
  the forcing is not independent evidence;
- the gain is sized by the **effective** sample size (§12.4), not the number of records.

## 2. The five validation modes

| Mode | What it tests | What it does not prove |
|---|---|---|
| **Descriptive retrospective** | compares a reconstruction or description with observations of the studied period that are independent of it | that the information was available at the time, nor any predictive ability |
| **Temporal out-of-sample** | builds on an earlier period, freezes, then tests on a later period | what was available at build time, if archives were consolidated afterwards |
| **Point-in-time replay** | steps forward chronologically, providing only the information available at each date | that the real system actually received that information |
| **Independent / mechanistic** | compares with measurements, experiments, operational documents, invariants or independent references | generalisation to other periods, regimes or domains |
| **Prospective** | records before the outcome and evaluates when the observation arrives | validity for periods or domains other than those observed |

These five modes are neither five successive stages nor a mandatory checklist. One or several are chosen according
to the nature of the claim.

### 2.1 What makes a temporal experiment valid

Building on 2000–2015 then testing on 2015–2020 is a legitimate temporal experiment if:

- target variables, metrics and criteria are defined before the test period is read;
- code, parameters, rules, variables and references are frozen;
- test-period results are used neither to choose nor to tune the model;
- data versions and revisions are kept;
- the fact that the build data are archives revised after the fact is stated.

This experiment does not show what the system would have known in 2015 if the build archives were consolidated after
that date.

### 2.2 Exploration and confirmation: two regimes, not two levels of rigour

Exploration and confirmation do not differ by the care taken, but by what is **consumed**.

- **In exploration**, the window looked at is **consumed** for every hypothesis of the same family. A rule found by
  looking at it can no longer be confirmed on those data: it must be confirmed on **new** data.
- **In confirmation**, the window is untouched when the rule is formulated, and the test is done on data that were
  not used to find it.

Three practical consequences:

1. **A look burns.** Searching a period means giving up establishing anything new in it. Poorly bounded
   exploration reduces the possible confirmation accordingly.
2. **The best of several variants is read shrunk.** When K variants are tried on the same data, the best one is an
   upward-biased estimator. It is then read **shrunk** — pulled towards zero by empirical shrinkage — to counter the
   winner's curse.
3. **The multiplicity correction comes afterwards**, and applies to the whole family of variants tried, never to the
   retained variant alone.

A repository that does not distinguish these two regimes produces results that cannot be confirmed, even when the
numbers are good.

### 2.3 Multiplicity is fixed before observation

The number of hypotheses looked at is part of the **method**, and is declared before the results are looked at. Two
non-negotiable rules:

1. **The correction is fixed in advance.** The correction method — and its level — is chosen in the
   pre-registration, not after seeing the p-values.
2. **Choosing the correction after the fact, according to the result, is not a correction.** It is
   **α-shopping**, and the result is no longer interpretable.

The method must match what the data structure actually allows:

| Data structure | What is guaranteed | What is not |
|---|---|---|
| independent hypotheses | control of the false-positive rate, per family | nothing beyond |
| arbitrary dependence (e-values, LOND) | FDR control under arbitrary dependence | that the hypothesis is about the **conditional expectation** of each unit, and that correlated units are **aggregated by cluster** before the test |
| bootstrap shrinkage | FDR under independence, or under PRDS | **nothing** under arbitrary dependence |

The third line is the nuance most often lost: a bootstrap shrinkage "corrects" multiplicity under narrower conditions
than the e-value it often replaces. And cluster aggregation is not optional: without it, none of these guarantees
holds.

## 3. Choosing the mode according to the claim

The mode is chosen according to what is claimed, never by default or convenience.

| If the claim is… | Minimal credible mode |
|---|---|
| "my reconstructed state matches what was observed" | descriptive retrospective, with an independent reference |
| "my model generalises in time" | temporal out-of-sample, with an explicit freeze |
| "my system would only have known what was available at date t" | point-in-time replay |
| "my mechanism actually produces this effect" | independent or mechanistic |
| "my signal predicts the coming revelation" | prospective |

A study that cannot change anything is not opened. A study whose possible evidence is out of reach is postponed,
not simulated by a weaker method presented as equivalent.

**No prospective validation is imposed by default.** It is demanding: it requires a sealed protocol, a waiting period,
a definition of failure in advance and the acceptance of a negative result. It is justified for a claim about the
future; it makes no sense for qualifying a computation, a naming convention or a format property.

## 4. Three temporal readings not to be confused

- **Operational replay**: what the system actually received and made usable.
- **Public replay**: what was publicly accessible, on evidence or a conservative bound.
- **Descriptive retrospective**: what consolidated archives allow to reconstruct today.

A public replay does not prove the system had received the information. A revised archive does not prove it was
available at the time. These three readings are never interchangeable in a result report.

## 5. Six distinct claims

| Claim | What it requires | What it does not prove |
|---|---|---|
| **Reconstruction** | a restored state, dated, located, with its provenance | that the state was known at the time, nor that it is predictive |
| **Estimation** | a quantity not directly observed, with its method and uncertainty | a direct observation, nor a causal mechanism |
| **Prediction** | a future value, issued at a given date, with an interval | a causal mechanism, nor a future reality |
| **Explanation** | a testable mechanism linking a change to an effect | that the effect is causally identified |
| **Causality** | an explicit identification strategy and its assumptions | generalisation outside the identification frame |
| **Simulation** | a result conditional on an imposed scenario | that the scenario will happen |

The implications are asymmetric and must be respected: a validated reconstruction is not automatically predictive; an
accurate prediction does not demonstrate the causal mechanism; a plausible mechanism is not an identified causal
effect; a consistent simulation does not prove the scenario will happen; a documented relation does not quantify its
propagation; a good financial performance does not retroactively validate the physical models.

**These six claims are the nature of a scientific claim, and nothing else.** They say nothing about the
**operational status** of a knowledge product: a usable product can carry an estimate, and an inconclusive product
can carry a reconstruction. The two notions are distinct, and one does not follow from the other
(`docs/CORE_CONTRACTS.md` §4.10).

The repository's nature vocabulary is narrower than these six claims: a derived quantity is `estimated`,
`reconstructed`, `predicted`, `simulated` or `derived`. Explanation and causality are not natures of a quantity but
**claim levels**: they belong in the report, not in the product type.

## 6. Reference, calibration, uncertainty, abstention

These four notions accompany every claim. They do not substitute for one another.

**Reference.** Every evaluation is compared with a reference: a simple one (persistence, the mean, a naive baseline)
or a competing method where a comparison is relevant. A performance without a reference cannot be interpreted. The
reference is chosen before the test.

**Calibration.** Announced probabilities must match observed frequencies. Evaluating an uncertainty is not limited to
a mean error: it checks that the announced interval contains the expected observation at the promised frequency. An
oversized uncertainty is not a certainty: it is imprecision presenting itself as precision.

**Uncertainty.** It is described according to what is known: data, parameters, model structure, initial conditions,
numerical approximation, scenario. Its form fits the context: interval, distribution, scenarios, bound, sensitivity,
or qualitative conclusion. A sophisticated distribution is not required if the data do not justify it. Coupled models
flag shared data, assumptions and errors; dependent outputs are not independent confirmations.

**Abstention.** A system declares what it cannot do. Every study declares its abstention, stopping and invalidation
conditions; every output may carry an explicit abstention policy. An absent value carries the reason for its absence
and is never zero. Abstention is a quality, not a failure: a system that never abstains on out-of-domain data is a
system whose out-of-domain performance means nothing.

## 7. Identifiability

Before interpreting an estimate strongly, check that the data actually allow the possible states or parameters to be
distinguished. If several explanations remain compatible, preserve the ambiguity rather than arbitrarily choosing a
precise value. Numerical precision is neither identifiability nor validity.

## 8. Inconclusive results

An inconclusive conclusion is a valid result. It may reflect insufficient observations, an unidentifiable state, an
inadequate reference, low statistical power or too narrow a domain. It is reported as such, with its cause. Absence of
evidence is never replaced by an unjustified proxy.

Every trial launched is recorded, including its error, its negative variants and its abandonment.

## 9. Guard against overcomplexity

No metric, method, layer, registry or artefact is added without showing which claim it helps to test. The simple
baseline is preferred when it answers the question. Evidence requirements are proportionate to the use and the risk
of the intended decision.

The doctrine chooses the mode of evidence. It does not create a second evaluation system, nor a validation that
duplicates the scientific logic.

## 10. Pre-registration, and what remains to be tooled

A pre-registration is not a document written to tick a box: it is a **lock** that makes the result interpretable. A
pre-registration exists as soon as it contains, frozen before observation:

- the claim tested, the domain, the period, the data;
- the method, its parameters, and the computation rule;
- the reference;
- **the multiplicity correction rule**;
- the success, failure and abandonment criteria.

The repository holds one: `docs/PRE-REGISTRATION-HYDRO-001.md`. It is **written**, not yet **tooled**.

Three checks are missing today, and as long as they are, the link between an experiment and its result remains
human:

| # | Missing check | What it would detect |
|---|---|---|
| 1 | **A report produced from a pre-registration** — no report can be published without the pre-registration that authorises it. | A result without a protocol, or a protocol written after the fact. |
| 2 | **An amendment dated and committed before the computation** — every protocol change carries a date and a commit, and precedes the computation. | A protocol rewritten after seeing the data. |
| 3 | **A pre-registration without a report** — an experiment opened and never closed is flagged. | An experiment silently abandoned, or a conclusion drawn elsewhere. |

These three checks are cheap, and they make the arrangement verifiable **by execution** rather than by memory.

## 11. Name a method for what it is

A misnamed method keeps doing harm as long as it carries another's name.

The temporal split of the evaluation is the example: what the repository implements is not a sliding window but a
**cumulative** split — each fold's training block contains **all** earlier values, not a moving window. Calling it
"walk-forward" without saying which of the two is written misleads about what the evaluation measures, and therefore
about what it proves.

The rule: **the name says what the method does, and the reference document says how**. If the two cannot be told
apart, the name is too general.

## 12. Four axes, and three verdicts that must not be confused

A scientific claim crosses four distinct questions. Confusing them is the most frequent source of error in
evaluation: a misplaced "no" becomes either a false negative or a refusal to answer.

| Axis | Question | Vocabulary | Owner |
|---|---|---|---|
| **1 — intrinsic validity** | is the value usable **in itself**? | `VALID` · `MISSING` · `INVALID` | socle and adapter |
| **2 — applicability** | does this product apply **to this context**? | `COMPATIBLE` · `INCOMPATIBLE` · `INDETERMINATE` | evaluation record |
| **3 — claim verdict** | what does the evidence allow **about this claim**? | `NOT_EVALUATED` · `SUPPORTED` · `REFUTED` · `INCONCLUSIVE` | evaluation protocol |
| **4 — product status** | **can** this published object be used? | `USABLE` · `DEGRADED` · `WITHDRAWN` · `INCONCLUSIVE` | publication contract |

Axes 1 and 4 exist in the repository (`src/torne/contracts/`). Axes 2 and 3 are missing, and they are not redundant:
axis 2 is about the **relation between a capability and a context**, axis 3 about **what the evidence establishes
about a proposition**. A claim can be `SUPPORTED` in its domain and `REFUTED` for a transfer; a product can be
`USABLE` while its applicability elsewhere is `INDETERMINATE`.

### 12.1 The three applicability verdicts, and the non-contamination rule

| State of the predicates | Verdict | What the evaluation declares |
|---|---|---|
| all satisfied | `COMPATIBLE` | applicability is **established** for this context |
| at least one violated | `INCOMPATIBLE` | non-transportability is **established** — and **stated** |
| none violated, at least one unknown | **`INDETERMINATE`** | comparability is established **neither way** |

> **Non-contamination: an "out of domain" finding can only be produced by an `INCOMPATIBLE` verdict.** An
> `INDETERMINATE` verdict produces an **abstention**, never an out-of-domain finding.

The twin rule closes the other direction of the shortcut: **a predicate is never "violated" by mere absence of
evidence**. "Satisfied" requires positive evidence, "violated" requires evidence of the violation; what has neither
is **unknown**.

Programme consequence: abstention becomes a **normal and valued output**. An unknown reference does not produce an
approximate comparison presented as valid: it produces a documented abstention.

### 12.2 What is carried where

Applicability predicates live in the **evaluation protocol**, not as mandatory fields of each product. A knowledge
product carries a **reference** to the evaluation that established it, and a **summary**. The eight predicates do not
become eight columns of a product's JSON: a product does not carry a grid it does not fill itself.

### 12.3 A refutation is knowledge

**A product's status is never degraded because an applicability was refuted.** Axis 3 is independent of axis 4: a
`USABLE` product whose applicability elsewhere is `REFUTED` **stays `USABLE`**; it is the `REFUTED` verdict that is
published, and it alone.

"Refuted" and "inconclusive" are not synonyms and must not become so: a refutation is a **result**, an inconclusive
is an **absence of result**. Confusing them means being unable to say that a method does not transfer.

### 12.4 The denominator, in seven elements

"How much data?" is not a question with a single answer. A denominator has seven elements:

1. **target population**;
2. **independent observation unit**;
3. **available observations**;
4. **observations actually used**;
5. **exclusions and their reasons**;
6. **effective size under dependence**;
7. **denominator of the generalisation**.

The effective size is a **diagnostic**: it never replaces the number of observations, and episodes or groups remain
the unit of generalisation.

The distinction these seven elements make visible: **precision of the observation** and **strength of the evidence
for transferability** are two things. In a leave-one-basin-out, 500 000 hydrometric records are not 500 000
independent physical systems. A product can be extremely precise on its observations and very weakly supported for
its transferability — and neither must hide the other. ATMO-001 measured it on four French stations: about 29 900
daily values carry about 2 000 independent days.

### 12.5 The three founding rules

1. **One platform, several physics.** TORNE shares its epistemology, provenance, temporality, evaluation procedures
   and computational capabilities; each domain keeps its physics, variables, judges and denominators.
2. **The unknown never becomes a certainty for convenience.**
3. **A refutation is knowledge.**

A programme decision follows: **TORNE does not seek a universal model of the world.** It seeks a capability to
produce, evaluate and reuse scientific knowledge from several physics, without confusing their structures.
Generalisation becomes a **testable claim**, never an implicit promise.
