# TORNE — Core contracts

**Objects, temporality, invariants**
**Status: contract.** This document fixes responsibilities, invariants and verifiable forms. It describes no
storage schema, no connector, no table, no service. Everything that depends on a particular source is explicitly
deferred (§6).

---

## 0. What this document is, and what it is not

It is **a contract**, in the sense that it says what must remain true whatever happens to the code. It exists so
that three things no longer depend on the implementer's style:

- what an object guarantees, and what it does not;
- at which instant a fact became true, known and acquired;
- which question a test must be able to ask to see that a rule holds.

It is **not** a storage architecture. It says neither where an observation lives, nor in what form, nor in what
format it travels. The programme forbids imposing a generic design before the data actually available are known
(`docs/PROGRAMME.md`); this document respects that by distinguishing, each time, what is **contractual** from what is
**deferred**.

It is **not** an implementation specification. The repository holds an executable form of these contracts in
`src/torne/contracts/` and `src/torne/acquisition/`: this document remains the **source**, the code applies it, and it
adds no building block. When the code and this document diverge, the document is wrong, and it is corrected.

### 0.1 What is verified, and how we know

Statements in this document are of three kinds, and the reader must be able to tell them apart:

| Kind | What grounds it | How it is checked |
|---|---|---|
| **Norm** | a decision taken by the project | the decision is written here, and its application is tested |
| **Practice** | the real behaviour of a source or a dependency | an observation, dated, replayable |
| **Inheritance** | the behaviour of a source repository | the repository, the commit and the exact file path, cited at the top of the module |

An inheritance statement cites the repository, the commit and the path. A source repository is **not** a dependency of
TORNE: it is neither installed, nor imported, nor consultable from this repository. It is only cited to say where a
reused block comes from, and to trace deliberate deviations.

---

## 1. Vocabulary

### 1.1 The five objects

These are **five distinct responsibilities**, not five layers, five tables or five services. An implementation may
place them in one module, one table, or separate processes: that changes nothing in the obligations below. What
distinguishes them is the **question** each answers alone.

| Object | Question it answers alone |
|---|---|
| **Source** | Where does the information come from, and under what conditions was it available? |
| **Raw Evidence** | Which raw content was actually retrieved, and is it still there, intact? |
| **Observation** | What did the source measure or report, at this instant and in these terms? |
| **Derived Variable** | What is the value of the quantity computed from these observations? |
| **Knowledge Product** | Which structured, versioned, reusable result came out of it? |

A **surface observation** (`EarthObservation`, `src/torne/contracts/earth_observation.py`) is an Observation whose
value is a field over a footprint and a time window rather than a scalar. It carries the same temporal, provenance and
absence obligations; it is not a sixth responsibility.

### 1.2 The three time dimensions

| Dimension | Question |
|---|---|
| **VALID_TIME** | When does the physical phenomenon exist, or when is the described fact true? |
| **KNOWN_AT** | When does the information become known or available **in its source**? |
| **INGESTED_AT** | When does TORNE actually acquire it? |

The three are **independent** and **not interchangeable**. No field may stand in for another.

### 1.3 Relations

Relations are a **data lineage**, not a pipeline of mandatory steps.

```text
Source ──1:N──> Raw Evidence ──1:N──> Observation ──N:M──> Derived Variable ──N:M──> Knowledge Product
                                             ▲                      │                        │
                                             └──────────────────────┴────────────────────────┘
```

- A **Source** has several **Raw Evidence**: one source produces content over time, under keys stable in that
  source.
- A **Raw Evidence** yields several **Observations**: decoding is deterministic and replayable.
- An **Observation** feeds several **Derived Variables**; a **Derived Variable** consumes several observations, and
  may consume other **Derived Variables**.
- A **Knowledge Product** consumes observations and derived variables, and cites the complete lineage.

What is **not** imposed: that a knowledge product pass through every object. A product may cite raw evidence directly
in its lineage; a derived variable may be produced from a single observation. The chain is a **dependency order**,
not an obligation of passage.

---

## 2. The five objects

### 2.1 Source

**Responsibility.** The Source is the sole guarantor of the **identity** and the **availability conditions** of a
piece of information: producing institution, dataset, access point, document or system. It describes what the source
is, what it publishes, in which units, with which revision policy, and under which access conditions.

**It guarantees** that the origin of every piece of information is named, that the conditions of its use are
recorded, and that a change of format or policy of the source is visible as a dated fact.

**Invariants.** A Source is identified stably and never merged with another. Its revision policy, units, time zone,
quality status and publication class (§3.11) are properties of the **source**, not of an isolated observation. Every
acquired piece of information is attached to a declared Source: an acquisition whose source is undeclared is a fact
to correct, not data to tolerate.

**It does not guarantee**: that the source publishes what it announces, nor when, nor that its data are complete or
accurate, nor that they will not be revised. Nor does it guarantee that the source will still exist tomorrow — the
disappearance of a source is a risk that provenance must make visible.

### 2.2 Raw Evidence

**Responsibility.** Raw Evidence is the sole guarantor of the **preservation of raw evidence**: the content actually
retrieved, as is, addressable, verifiable, never lost. It is the only original truth: everything else can be rebuilt
from it.

**It guarantees** that what was received is still readable, that its digest is stable, that its content was not
modified afterwards, and that a "nothing here" response is kept as such — with its acquisition date — instead of
disappearing.

**Invariants.** Raw content is **written once**, under its digest; it is never rewritten. When the content of a key
changes, that is a **new version**, the old one staying readable and unchanged. Identical re-collected content is
idempotent. Every acquisition is journaled, including its failure.

**It does not guarantee**: that the raw content is understood, nor that it suffices to produce the desired
observation. It does not guarantee that the source returned what it should have. It carries no interpretation:
analysis never touches it, it can be re-parsed.

> **Raw data is never silently overwritten** (`docs/PROGRAMME.md`). The verifiable form is the existence of a second
> version record, never a mutation of the old one.

### 2.3 Observation

**Responsibility.** The Observation is the sole guarantor of **semantic content**: a measurement or piece of
information as provided by its source — its value, unit, spatial reference, quality status, precision, and temporal
membership.

**It guarantees** that what is stated is exactly what the source said, in the source's terms; that the value can be
rebuilt from the raw evidence; that its status (provisional, approved, estimated) travels with it; and that an absence
is a **qualified** absence, never a zero.

**Invariants.** Every observation carries its three time dimensions, or the explicit state of their absence (§3).
Every observation carries its unit and its spatial reference. An absent observation carries a `missing_reason` from a
controlled list (§3.8). An observation is attached to an identifiable Raw Evidence from which it can be re-derived.

**It does not guarantee**: that the measurement is right, nor that the source is exhaustive, nor that the value is
final. A provisional observation is a complete observation, not a degraded one. Nor does it guarantee that the
observation is the right unit of analysis: a daily mean and an hourly measurement are two observations of different
granularities, not two versions of the same observation.

### 2.4 Derived Variable

**Responsibility.** The Derived Variable is the sole guarantor of the **computation rule**: a value computed or
estimated from one or several observations, whose method, parameters, inputs and uncertainty are known.

**It guarantees** that the value is reproducible from the observations consumed, that the computation rule is
identified and versioned, and that the variable never presents itself as a source observation.

**Invariants.** A derived variable cites all its inputs, transitively down to raw evidence. It carries its own
temporality: `VALID_TIME` is that of the phenomenon it describes; `KNOWN_AT` and `INGESTED_AT` are those **of the
computation**, never those of the source. It carries an uncertainty qualification fitted to what is actually known
(`docs/RESEARCH_AND_VALIDATION.md` §6).

> **Main leakage point.** A variable computed on 21 October from observations published on 18 October is only known
> from 21 October. Giving it the `KNOWN_AT` of its inputs passes a later reconstruction off as one available in real
> time.

**It does not guarantee**: that the computation is right, nor that the inputs are the right ones, nor that the
variable has a physical meaning. Nor stability: two runs on the same inputs give the same result **only if** the
computation rule, parameters and environment are identical.

### 2.5 Knowledge Product

**Responsibility.** The Knowledge Product is the sole guarantor of the **published version**: a structured, versioned
result, produced by a model or a reconstruction, meant to be reused, audited or consumed independently.

**It guarantees** a version, a timestamp, complete provenance down to the sources, a domain of validity, a qualified
uncertainty and an explicit status: usable, degraded, withdrawn, or inconclusive (`docs/ARCHITECTURE.md` §4).

**Invariants.** A product is publishable only if its lineage is complete and verifiable. A published product is not
rewritten: a correction produces a **new version**, and the old one stays consultable. An inconclusive product is a
valid result, reported as such, with its cause (`docs/RESEARCH_AND_VALIDATION.md` §8). A product cites no observation
that was not admissible when it was established; and its establishment instant precedes neither the production of the
result it publishes nor the establishment of the record that carries it: **a product does not precede what it
publishes**.

**It does not guarantee**: that the product is true, nor that it stays true, nor that it is reusable outside its
domain of validity. It is not a registry and does not catalogue what exists (`docs/ARCHITECTURE.md` §4). It does not
retroactively validate upstream models.

---

## 3. Temporal semantics

### 3.1 The three dimensions, and what is not one

`docs/ARCHITECTURE.md` §6.2 refers to "the canonical distinction between validity, publication, receipt, availability
and use times". This contract **stores only three**, because the other notions are either derivable or query
parameters. Storing a fifth dimension would introduce a redundancy nothing governs.

| Architecture notion | Treatment here |
|---|---|
| Validity time | **Stored dimension**: `VALID_TIME`. |
| Publication time | **Stored dimension**: `KNOWN_AT`. |
| Receipt time | **Stored dimension**: `INGESTED_AT`. |
| Availability time | **Derived function**: `usable_at`, never a free field (§3.2). |
| Use time | **Query parameter**: the decision instant, never carried by the data. |

Two refinements of the architecture:

- **The date declared by the issuer** is not a sixth dimension. It is source metadata, which feeds `KNOWN_AT` when the
  source allows it to be established, and must stay distinct from the instant of *release* when the source
  distinguishes them (some issuers timestamp a document they release later). The contract requires the two to be
  **named separately** when the source provides them separately; their value per source is deferred (§6).
- **The decision instant** ("what did we know at *t*?") is never stored with the data: it is the query's `asof`. A
  datum carrying its own use instant would be a contradiction.

### 3.2 The decision point of view

The central rule, unambiguous:

> A piece of information is **usable** at instant *t* if and only if it was **known in its source** at the latest at
> *t* **and** TORNE had **acquired** it at the latest at *t*.

In other words, the usability instant is the **maximum** of the two:

```text
usable_at = max(KNOWN_AT, INGESTED_AT)
```

Three consequences, each verifiable:

1. **`usable_at` is never stored.** It is a function of the two dimensions, computed at query time. A stored
   `usable_at` would be a third copy liable to diverge.
2. **Information acquired before it was known is an error case, not an exploit.** If `INGESTED_AT < KNOWN_AT`, one of
   the two is wrong: the datum is doubtful and must be flagged as such, not exploited.
3. **The natural order is `VALID_TIME` ≤ `KNOWN_AT` ≤ `INGESTED_AT`**, with one named exception: the re-import of a
   historical archive (§3.3), where `INGESTED_AT` is the **original** acquisition date, not that of the re-import.

The rule is identical, word for word, to that of `athanor.kernel.clock` (`athanor/src/athanor/kernel/clock.py:9-12`):
"a point is usable at `asof` <=> `usable_from(published_at, known_at) <= asof`, with
`usable_from = max(published_at, known_at)`. A point without `known_at` is never usable." The contract takes the rule
over; it **changes the interpretation of the names**, which is the subject of §5.5.

### 3.3 Instants, civil dates, intervals, series

**Instants.** An instant is a point in time. It is stored in **UTC**, in ISO 8601 with an explicit offset. An instant
without a time zone is **forbidden**: it is not "assumed UTC", it is refused at entry. Conversion to UTC happens
**once**, at decoding, and is recorded.

**Civil dates.** A civil date is a calendar day, without a time. It is a type distinct from an instant, and the two do
not convert into each other without an explicit decision. A stored civil date always comes with the civil context
that makes it interpretable (the calendar, and the time zone when it results from grouping). A civil date never
degrades into an instant by default: the date → 00:00 instant step is a **source decision**, not an implementation
convenience (§6). Indexing by civil day uses the civil day **in the declared zone**, never the UTC day of the stored
instant.

**Intervals.** An interval is a pair `[start, end)`, **half-open**, with explicit bounds and a consistent internal
granularity. An exclusive end prevents a discrete observation characterising a period from belonging to two
neighbouring periods. An interval with unknown bounds is not an interval: it is a qualified absence. An interval is
split into instants only if the source allows it.

**Time series.** A series is a **set of observations**, never a value. Each point keeps its own status, precision and
revision. A series **does not inherit** its last point's status: a series whose last 90 points are approved and whose
first 10 are provisional stays a mixed series, and the contract requires it to be qualified as such.

**Grouping.** An aggregation (a daily mean, a weekly total) produces a **new observation**, not a derived one: its
value is a source's. It therefore carries its own lineage, time dimensions and status.

### 3.4 Time zones

The rule has three parts, and it is **unique**:

1. A civil date is interpreted with the time zone **the source declares** — never that of the machine or of the
   execution context. When the source declares none, the zone is an explicit argument of the reading, never a
   default.
2. Conversion to UTC happens at the boundary: at decoding, once, and the result is kept.
3. The original civil instant is kept next to the result.

A simple non-regression test: the same raw datum replayed on a machine in another time zone gives the same result.
That is the verifiable form of "the time zone does not depend on who runs the code".

TORNE **does not inherit** the time-zone rules of the former BORÉE. `boree/src/boree/temps.py:86-95` (the `horaire`
and `local` functions, which average quarter-hours and merge the two UTC hours falling on 2 a.m. local time) is a
generic, tested pattern, but its **content** is tied to the electricity market and out of scope (§5). What TORNE keeps
is the idea that a local hour can be ambiguous — so conversion must be done and kept, not recomputed at reading time.

### 3.5 Variable precision

Two sources do not mean the same thing by "precision", and the contract separates them:

- **Declared resolution**: what the source says of its measurement step (hourly, daily, weekly).
- **Real uncertainty**: what is known of the accuracy of the value.

A value with hourly resolution carries an uncertainty that is not zero merely because the source does not publish it.
The contract requires an observation **without qualified uncertainty** to say so explicitly, rather than suggest a
precision nobody established. The form fits what is known (`docs/RESEARCH_AND_VALIDATION.md` §6): interval,
distribution, scenario, bound, sensitivity, or qualitative conclusion.

Presentation rounding **is not** uncertainty: rounding at display does not reduce the uncertainty of the stored value.

### 3.6 Revised observations

**Central rule: revision does not rewrite history.**

A revision creates a **new version** of the observation, not a mutation of the old one:

- same natural key (source + entity + valid time + quantity);
- `KNOWN_AT` and `INGESTED_AT` later than those of the version replaced;
- an explicit link to the previous version, so the revision chain can be walked;
- its own status (a revision may move an observation from provisional to approved).

The previous version **stays readable**. That is what makes point-in-time reconstruction possible: querying the state
at 15 October returns the version believed that day, not the one of 25 October.

A revised observation is therefore **two observations**, not an observation and its history. Aggregating them,
averaging them or keeping only the latest is a reconstruction error, not a simplification.

**What revision does not say.** A revision proves that information changed; it does not prove **when or why**, unless
the source says so. A source that does not date its revisions does not allow the revision chronology to be rebuilt:
the contract then requires it as a **qualified absence** (§3.8), and whether the revision history can be rebuilt
becomes a source question, not a design one (§6).

### 3.7 Provisional information

Provisional information is **information**, not an absence and not a tolerated approximation. Three rules:

1. **It is kept.** A provisional value is a complete observation; it is not set aside until approval.
2. **It carries its status.** The status is a property of the value and travels with it, up to the knowledge product.
3. **It is not confused with an approved value.** A product consuming provisional observations says so; it does not
   present the whole as settled.

The strong consequence: the qualification of a **product** depends on that of its inputs. A product whose inputs are
all approved is not thereby "approved" — the product's status is its own.

The status vocabulary is **closed and minimal** — a declared value, a value estimated by the source, a provisional
value, an approved value, a value of unknown status — but **mapping a source's statuses onto it is deferred** (§6):
saying that a USGS "provisional" equals "provisional" is a claim about the source, not about the contract.

### 3.8 Absent information

**Absent ≠ zero.** It is a rule of the canonical vocabulary, stated twice in the repository: `docs/ARCHITECTURE.md`
§6.2 and `docs/RESEARCH_AND_VALIDATION.md` §6.

The contract names the field carrying the reason: **`missing_reason`**. The name is this document's choice; the notion
is canonical. Its list of values is **controlled** and grows deliberately — but source-specific values are deferred
(§6). A reason for absence describes **what is missing**, never **what failed during retrieval**: that is the next
point.

**Three distinct absences, never confused:**

| Absence | What it means | What it requires |
|---|---|---|
| **Not measured** | the source provides no value for this fact | `missing_reason` |
| **Not yet published** | the value will exist, not yet | `missing_reason` + the expected date |
| **Collection not attempted** | TORNE did not go and look | `missing_reason` + the trace of the non-attempt |

The third deserves a word: the former BORÉE learned the difference the hard way.
`boree/src/boree/exploitation/garage.py:95-121` distinguishes `en_attente` (copy not sent, deferred) from
`absents_locaux` (present in the index, absent from disk): a copy **not attempted** is stated **with its reason**, not
as a missing copy. A TORNE absence can have three causes that must not be confused: the data does not exist, has not
yet appeared, or was not looked for. Confusing them amounts to announcing a measurement of zero.

And the converse: **an absence is never filled by an assumption**. A `missing_reason` is never replaced by an
estimate, an interpolation or a default value (`docs/PROGRAMME.md`).

### 3.9 Unknown publication: an explicit, usable ignorance

This is the most demanding point of the contract: **if the source does not allow the initial publication date to be
known, do not invent it**.

The contract does not merely forbid it. It makes the ignorance **usable**, by distinguishing three states of
publication knowledge, carried by the observation:

| State | What is known | Usability rule |
|---|---|---|
| **Established** | the initial publication instant is known | `usable_at = max(publication, ingestion)` |
| **Bounded** | a **lower bound** is known: from it on, the information was certainly available; before, unknown | admissible from the bound, **not before** |
| **Unknown** | neither instant nor bound | **not admissible** in point-in-time reconstruction, and the observation says so |

Why a bound rather than a flat refusal: `docs/RESEARCH_AND_VALIDATION.md` §4 admits a "public replay: what was
publicly accessible, **on evidence or a conservative bound**". A conservative bound is therefore acceptable, provided
it is conservative — that is, it never **overestimates** availability. It produces a censoring interval, not an
invented date: the information was there from *t* on, whether it was there before is unknown.

This is where the contract **diverges from `athanor`**: `athanor/src/athanor/kernel/clock.py:39-46` sets
`usable_from(published_at=None, known_at=…) = known_at`, that is, **replaces an unknown publication with the ingestion
date**. That is exactly the filling-by-assumption `docs/PROGRAMME.md` forbids. TORNE does not take that fallback: an
unknown publication stays unknown, and the observation is not admitted in point-in-time reconstruction.

An **upper** bound on publication (an archive version that bounds publication from above) is not representable yet;
it is recorded as a deferred contract extension (`docs/PROGRAMME.md` §6, A2).

### 3.10 Operational replay, public replay, descriptive retrospective

`docs/RESEARCH_AND_VALIDATION.md` §4 sets three distinct temporal readings, "never interchangeable in a result
report". The contract makes them distinguishable at the data level, through a single marker:

- **Operational replay**: what TORNE actually received and made usable. An observation acquired by re-importing a
  historical archive **does not belong to it** at import time: it belongs to the original acquisition date, and is
  marked as such.
- **Public replay**: what was publicly accessible, on evidence or a conservative bound. This is the default mode of a
  reconstruction.
- **Descriptive retrospective**: what consolidated archives allow to rebuild today.

The marker is indispensable: `athanor/src/athanor/data/rawstore.py:226-233` already does the same through a dedicated
path (`import_archived`, which receives an original `known_at` and marks the row `legacy`). TORNE takes the **need**,
not necessarily the syntax.

### 3.11 Per-source instantiation of `KNOWN_AT` — the four source classes

§3.2 gives the **form** of the usability rule; §3.9 gives the three **states** of publication knowledge. What was
missing is **how to establish `KNOWN_AT` from what the source actually exposes**.

It is not a provider problem, and no paid feed solves it: the cross-domain review of 31 October 2026 found the same
pattern in every physical domain examined — a power-grid API without delivery timestamps, a satellite catalogue that
separates the origin date from the publication date by months, a hydrological history explicitly **backfilled**.
Availability must therefore be **constructed**, source by source, by TORNE's semantics.

**The single rule.** Each source is classified by what it exposes, and the class determines the publication state,
hence admissibility. A state more favourable than the source allows is never chosen.

| Class | What the source exposes | State | Rule for establishing `KNOWN_AT` |
|---|---|---|---|
| **P — timestamped publication** | the publication instant of each version | **established** | `KNOWN_AT` = that instant. The only case where `KNOWN_AT` is a date rather than a bound. |
| **B — publication bound** | a lower bound: "from this instant on, the information was certainly available", nothing more | **bounded** | `KNOWN_AT` = the bound. The observation is admitted **from** the bound, not before (INV-11). The censoring interval is kept and reported. |
| **C — documented publication cycle** | a documented publication cycle (for example a weekly bulletin every Wednesday) and values nominalised to that cycle | **bounded** | `KNOWN_AT` = **the earliest possible** publication instant of the cycle concerned, from the documented calendar. Conservative by construction. |
| **N — no publication** | no instant, no bound, no cycle: backfilled history, or an API without delivery timestamps | **unknown** | No `KNOWN_AT` is invented. The observation is **not admitted** in point-in-time reconstruction. It stays usable as **descriptive retrospective**, and the product using it declares so (`replay_mode`). |

The class is carried by `Source.publication_class` (`PublicationClass`, `src/torne/contracts/observation.py`); `None`
means "not established", which refuses point-in-time admission.

**Three non-negotiable consequences.**

1. **The class follows from the source, not from convenience.** A source falls into class N as soon as it exposes no
   usable timestamp, however good its content. The fallback `usable_at = INGESTED_AT` rejected in §5.6 **is not
   reopened**.
2. **A class N source is not disqualified**: it is reclassified. It then carries valuable information — a
   retrospective description — and its use is declared, not hidden.
3. **The class is a property of the source, versioned with it.** A change of format or publication cycle is a
   revision of the source: it creates a new version of the source record and can move observations from class C to
   class N.

**What remains, and is not done here.** This section gives the **classification rule**. It does not give, for each
real source, the effective class or bounds: that is **source qualification** (`docs/SOURCES.md`) and must be
established **by execution** — a source whose publication cycle is assumed but not verified is a class N source, not
class C.

---

## 4. Verifiable invariants

Each invariant is stated as a rule a test can check, or as a question a test must answer **yes** or **no**.

### 4.1 Preservation of raw evidence

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-01** | Raw content is written once, under its digest. | Does re-collecting the same content create a second entry? Expected: no. |
| **INV-02** | A content change for the same key creates a new version; the old one stays readable and unchanged. | After the source changes, do both versions exist with the old digest unchanged? Expected: yes. |
| **INV-03** | Every raw acquisition is recorded, including its failure and its "nothing here" status. | Did the acquisition produce a journal entry? Expected: yes, in every case. |
| **INV-04** | The acquisition journal is append-only. The contents it references are addressed by digest: modified content no longer matches its digest. Journal lines are not chained to each other, so modifying an already written line is not detected by the journal. | Does an appended line touch the others? Does modified content keep its digest? Expected: no and no. Line chaining is a known limit, not a guarantee. |
| **INV-05** | No raw content is deleted because a newer version exists. | Is the old version still readable? Expected: yes. |
| **INV-06** | Deduplication loses nothing: identical content already present is neither rewritten nor lost. | Do two acquisitions of the same content lead to one stored content and two acquisition traces? Expected: yes. |

### 4.2 Temporality

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-07** | Every observation carries its three dimensions, or the explicit state of their absence. | Is there an observation without the three fields or an explicit absence state? Expected: no. |
| **INV-08** | `usable_at` is a derived function, never a stored field. | Is there a `usable_at` field in the data? Expected: no. |
| **INV-09** | `usable_at = max(KNOWN_AT, INGESTED_AT)`. | For a given pair of dates, does the computation return the maximum? Expected: yes. |
| **INV-10** | An unknown publication is never replaced by the ingestion date. The publication state follows from what the source **exposes**, established by verification (§3.11). | When `KNOWN_AT` is unknown, is the observation admitted in point-in-time reconstruction? Is the source class established by verification? Expected: not admitted, state "unknown"; class established by execution. |
| **INV-11** | A bounded publication is only admitted from its bound. | Does a query at `t` before the bound return the observation? Expected: no. |
| **INV-12** | A revision is invisible before its revision date. | Does querying the state at `t` before the revision return the previous version? Expected: yes. |
| **INV-13** | A revised version coexists with the version it replaces. | Are both versions readable? Expected: yes. |
| **INV-14** | An acquisition by archive re-import carries the mark of its origin and does not present itself as acquired by TORNE at re-import date. | Does an operational replay query exclude this observation? Expected: yes. |
| **INV-15** | No instant is stored without a time zone; a civil date is never stored as an instant. | Is there a naive instant? Expected: no. The refusal is at entry, not an after-the-fact fix. |
| **INV-16** | The result of a computation does not depend on the time zone of the machine running it. | Does the same raw datum replayed in two time zones give the same result? Expected: yes. |
| **INV-17** | A derived variable carries as `KNOWN_AT` the computation instant, never that of its inputs. | Is a variable computed on 21 October from inputs published on 18 October known on 18 October? Expected: no, on 21 October. |

### 4.3 Absence, status, unit

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-18** | An absent value carries a `missing_reason` from a controlled list. | Is there an absent value without a reason, or a reason outside the list? Expected: no. |
| **INV-19** | Absent ≠ zero. | Are an absence and a zero distinguishable, and can a conversion turn one into the other? Expected: distinguishable, not convertible. |
| **INV-20** | Absence and non-attempt are distinguished. | Does the entry say which one happened? Expected: yes, and the two do not overlap. |
| **INV-21** | Provisional information is kept and carries its status. | Does the provisional observation exist in the corpus with its status? Expected: yes. |
| **INV-22** | A provisional value and an approved value are never confused in a product. | Does the product consuming them distinguish them? Expected: yes. |
| **INV-23** | Every observation carries its unit and its spatial reference. | Is there an observation without unit or spatial reference? Expected: no. |
| **INV-24** | A series does not inherit its last point's status. | Is a series with mixed points qualified as mixed? Expected: yes. |

### 4.4 Provenance and lineage

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-25** | Every observation attaches to identifiable raw evidence. | Can one go back from the observation to the raw digest? Expected: yes. |
| **INV-26** | Re-parsing the raw content with the same parser gives the same observation. | Does re-parsing produce an identical result? Expected: yes. |
| **INV-27** | Every derived row carries a minimal lineage: source, key, digest, knowledge instant. | Are the four elements present and non-empty on every derived row? Expected: yes. |
| **INV-28** | Raw is the only truth; derived is rebuildable. | Does rebuilding from raw give the same result as the stored derived value? Expected: yes. |
| **INV-29** | A derived variable knows all its inputs, transitively down to raw. Each cited input is the **canonical object** of the record: an identifier cannot designate another content. | Can the set of consumed observations be rebuilt from the product? Is each cited input the object the record carries? Expected: yes. |
| **INV-30** | A knowledge product cites no observation that was not admissible at its own establishment instant. That instant precedes neither the production of the published result nor the establishment of the record carrying it. | Do all cited observations have `usable_at ≤` the product instant? Is the product instant later than what it publishes? Expected: yes. |
| **INV-31** | A published product is not rewritten. | Does a correction create a new version, the old one staying consultable? Expected: yes. |

### 4.5 Anti-leakage

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-32** | Every table entering TORNE has a **synthetic store** whose every value encodes its date. | In the synthetic store, does the value tell which day it comes from? Expected: yes. |
| **INV-33** | The forbidden realised value carries a distinct sentinel (by convention −1), never 0. | Is the sentinel distinguishable from a legitimately zero value? Expected: yes. |
| **INV-34** | A point-in-time reconstruction returns no inadmissible observation. | Does the query at `t` return an observation with `usable_at > t`? Expected: never. |

> The synthetic store is a **decision already taken**: it is set up from the first table, and the reference technique
> is that of the former source repository — each value encodes its date, the forbidden realised value is −1. This
> document makes it an **invariant**, not a good practice.

### 4.6 The testable form

The general rule that makes these invariants usable: **an anti-leakage test is not a test of values, it is a test of
dates**. It does not check that a value is correct; it checks that a value **could not have been produced by
information later than the simulated instant**.

The canonical form is the **synthetic store**: write into the store a datum whose **value** is the date it comes from,
so that a temporal leak reads as a wrong number rather than a code subtlety. The evaluation suite uses this form
(`tests/test_evaluation.py`).

### 4.7 Numerical reproducibility

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-35** | Global randomness is never touched: the seed is passed to the component, which builds its own generator. | Does a run with a fixed seed give the same result as another run with the same seed? Expected: yes. |
| **INV-36** | A sampling component is deterministic for a fixed seed. | Are two draws of the same component, same seed, identical? Expected: yes. |

### 4.8 Conformity of an acquisition

Acquisition is the only place where "I obtained bytes" and "I obtained what I asked for" can be confused. The
repository keeps the two apart, and that is a contract requirement, not an implementation precaution.

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-37** | **Raw data is not semantic conformity.** An adapter confronts what it received with what it asked for: the requested identifiers are those that come back, and it does not assume the provider obeyed. **A filter echoed in the URL is not evidence of filtering.** A criterion the response does not allow to verify is recorded as **unverifiable**, never as satisfied. | Does a request for a non-existent identifier come back with that identifier's rows? Expected: no, and the verdict is `non_conforme`. |
| **INV-38** | **Exhaustiveness is qualified per source.** A successful HTTP response does not prove the provider returned every expected observation. | Does the outcome carry an exhaustiveness — `declared_exhausted`, `truncated` or `undeclared`? Expected: yes, always. |
| **INV-39** | **An adapter error is a result, not an exception.** A malformed response produces a structured outcome (`failed` or `partial`), never an exception leaving the acquisition with nothing recorded. | Does a malformed response produce an outcome and a trace? Expected: yes, `failed` or `partial`. |
| **INV-40** | **Conformity is qualified, not assumed.** A conformity verdict is `conforme`, `non_conforme`, `indeterminate` or `non_applicable`, established by execution, with a reason. `indeterminate` is an **abstention** — a requested criterion could not be verified — not a finding. **The gate only opens on `conforme`**: an abstention authorises no more than a non-conformity. The verdict only speaks of conformity; the acquisition status only speaks of acquisition, and the `exploitable` gate is the only question to ask before building observations. | Is a verdict produced without querying the source? Is an outcome with indeterminate conformity exploitable? Is a non-conforming outcome declared an acquisition failure? Expected: no, no, and no. |

The verdict values (`conforme`, `non_conforme`, …) and the conformity API names (`Conformite`, `CritereConformite`,
`VerdictConformite`) predate the English rule; they are part of the shared contract and are translated in one
dedicated change (`docs/PROGRAMME.md` §6).

### 4.9 Secrets and credentials

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-41** | **A secret only travels by reference.** What is recorded — journal, manifest, fingerprint, report, message — carries a credential reference, never the value. | Does a secret's value appear in a recorded medium? Expected: no. |
| **INV-42** | **A credential does not cross an origin.** A change of host, port or scheme drops credentials; a downgrade from `https` to `http` drops them too. | Does a redirect to another origin transmit the credential? Expected: no. |

### 4.10 Nature of a result and operational status

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-43** | **The nature of a result and the operational status of a product are distinct, and do not follow from each other.** A derived quantity carries its nature (`estimated`, `reconstructed`, `predicted`, `simulated`, `derived`); a knowledge product carries its operational status (`usable`, `degraded`, `withdrawn`, `inconclusive`). The repository implements two of the four axes; the other two, and the non-contamination rule that governs them, are set as doctrine (`docs/RESEARCH_AND_VALIDATION.md` §12). | Can an `inconclusive` product carry an estimate? Does a `usable` product always carry a nature? Expected: yes and yes. |

### 4.11 What uses the future, and what was estimated

| Ref. | Invariant | Verifiable form |
|---|---|---|
| **INV-44** | **An output that uses future information is declared as such, and the declaration is kept with the product.** Rauch–Tung–Striebel smoothing rebuilds a historical state using observations **later** than the instant it estimates: a better reconstruction, but not an estimate that was available at that instant. Filtering and smoothing are therefore two distinct outputs, and the second is named in `ModelResult.outputs_using_future`. A declared output must exist. | Is a smoothed output declared as using the future? Is the declaration kept in the record? Expected: yes and yes. |
| **INV-45** | **Parameters a method estimated are kept with the product.** Configuration parameters are the *requested* ones; the *used* ones — estimated on the training history, when the method does so — are carried by the result and kept in the record. An artefact that does not say which parameters were used cannot be replayed: the estimate becomes an unverifiable claim. | Does the record carry the **used** parameters? Is an estimated parameter distinguishable from the requested one? Expected: yes, and the difference is visible. |

> Both invariants answer the same question in two forms: is *what was computed* reproducible? A declaration not kept
> with the product protects nobody; it only protects whoever wrote it.

---

## 5. Reuse policy, and the "one of each" arbitrations

### 5.1 The rule, and the four categories

TORNE does not write what already exists elsewhere when what exists is good. Before writing a block, one looks: it may
already have been written, audited and tested in a repository the project controls.

A candidate block is classified in **exactly one** of four categories, and the category is written:

| Category | Meaning |
|---|---|
| **REUSE** | the code is taken as is, its origin declared at the top of the file |
| **ADAPT** | the code is taken and modified, the modification justified |
| **REIMPLEMENT** | the block is rewritten: the duplicate is tied to the original domain, or the original is not reusable as is |
| **REJECT** | the block is not taken, and the reason is written |

Four conditions for a block to enter as REUSE or ADAPT:

1. **the licence** is read in the file itself, never assumed;
2. **the origin is verifiable** — repository, commit and exact path noted at the top of the module;
3. **one decision per component** — the repository never hosts two implementations of the same responsibility;
4. **the import is real** — a dependency never imported is not a dependency.

No block enters TORNE without being, at least, **classified**.

### 5.2 What TORNE took, and from where

Four statistical primitives come from a **private** historical repository of the owner, hence reusable without licence
reservation. They were taken as internal rewrites: the only requirement is traceability of origin.

| Need | TORNE module | Published reference |
|---|---|---|
| Ordinary least squares, CR1 robust standard error | `src/torne/methods/regression.py` | Cameron, Gelbach & Miller (2011), *REStat* 93(2) |
| Paired Diebold–Mariano test, HAC long-run variance | `src/torne/methods/calibration.py` | Diebold & Mariano (1995), *JBES* 13(3); Newey & West (1987), *Econometrica* 55(3) |
| CUSUM mean break | `src/torne/methods/breaks.py` | Ploberger & Krämer (1992), *Econometrica* 60(2) |
| Minimal detectable effect, sample size, power | `src/torne/methods/power.py` | Lehr (1992), *Stat. Med.* 11(10); Kish (1965) |

Each file states at its top the source repository, the commit (`athanor@6dacc87`), the exact path, the licence status,
third-party dependencies and the published reference. The corresponding tests check results against the published
definitions — `scipy`, `statsmodels` — and **not** against an internal reimplementation.

**Original writing.** Other modules come from no historical repository: they are written against the literature, which
they cite module by module, with the same requirements — one reference per routine, a test checking the result against
the published definition. Their provenance is **a publication**, not a commit.

| Need | TORNE module | Published reference |
|---|---|---|
| State-space Kalman filter, local linear trend, Rauch–Tung–Striebel smoothing | `src/torne/methods/kalman.py` | Durbin & Koopman (2012), ch. 4; Rauch, Tung & Striebel (1965), *AIAA Journal* 3(6) |
| Paired forecast comparison and regime-break search | `src/torne/methods/compare.py` | Diebold & Mariano (1995); Newey & West (1987); Ploberger & Krämer (1992) |
| CRPS, interval score, pinball score, PIT and calibration diagnostics | `src/torne/methods/scores.py` | Gneiting & Raftery (2007), *JASA* 102(477); Winkler (1970), *JASA* 65(290); Ferro (2014), *QJRMS* 140(681) |
| Effective sample size, block bootstrap, cluster bootstrap, sensitivity to the independent unit | `src/torne/methods/dependence.py` | Politis & White (2004), *Econometric Reviews* 23(1); Künsch (1989), *Ann. Statist.* 17(3); Geyer (1992), *Biometrika* 79(3) |
| Multiplicity control: Benjamini–Hochberg, Bonferroni, Romano–Wolf max-t | `src/torne/methods/multiplicity.py` | Benjamini & Hochberg (1995), *JRSS-B* 57(1); Romano & Wolf (2005), *Econometrica* 73(4) |
| Spatial reference, footprint, raster grid; surface observation | `src/torne/contracts/spatial.py`, `earth_observation.py` | STAC 1.1.0; OGC API – Features Part 1 (ISO 19168-1); GeoJSON RFC 7946; GDAL affine transform convention |

All stochastic routines — the bootstrap, the Romano–Wolf multiplier — take an explicit seed and build their own
generator: global randomness is never touched (INV-35, INV-36).

### 5.3 One responsibility, one implementation

The "one of each" arbitration, stated on the real state of the repository:

| Responsibility | Single implementation in TORNE |
|---|---|
| Point-in-time raw store | `src/torne/acquisition/store.py` |
| Connector contract and conformity | `src/torne/acquisition/contracts.py` |
| HTTP client and transport | `src/torne/acquisition/transport.py`, `fetcher.py` |
| Credentials by reference | `src/torne/acquisition/credentials.py` |
| Canonical fingerprint | `src/torne/contracts/fingerprint.py` |
| Acquisition journal | `src/torne/acquisition/store.py` (`manifeste.jsonl`) |
| Spatial vocabulary | `src/torne/contracts/spatial.py` |
| Replayable model execution | `src/torne/execution/runner.py` |
| Product record and lineage verification | `src/torne/knowledge/record.py` |
| Statistics | `src/torne/methods/` |

**Recorded exception.** The day-of-year climatology and anomaly exist twice, in `src/torne/hydrology/anomaly.py` and
`src/torne/atmosphere/anomaly.py`. Both follow the same rules (reference bounds filter the record; the day key is the
civil day in a given zone). Choosing the single owner is an open decision (`docs/PROGRAMME.md` §6).

### 5.4 What was set aside, and what must not be rewritten blindly

The other blocks seen in the historical repositories were set aside for three distinct reasons: tied to the original
domain, already covered by a TORNE block, or dependent on infrastructure the socle does not want. The audited
repositories are **not** dependencies of TORNE; what remains is the rule of §5.1.

Three families stay deliberately **not reimplemented** until a need calls for them. They are cited so that their
conditions are known when the need comes:

- **e-values and LOND.** FDR control under arbitrary dependence, but **only** if the hypothesis is about the
  **conditional expectation** of each unit and correlated units are **aggregated by cluster** before the test. Cluster
  aggregation is a prerequisite, not an option. Bootstrap shrinkage only gives FDR under independence or PRDS — **not**
  under arbitrary dependence.
- **The "burn / shrink" exploration cycle.** An exploratory look **consumes** the window it looks at, for every
  hypothesis of the same family: a rule found there is then confirmed only on new data. The best of K variants is read
  *shrunk*, to counter the winner's curse. The cycle only makes sense if the hypothesis family is defined.
- **A shared alpha budget.** Splitting an alpha between hypotheses of one family, with explicit governance of who
  consumes it.

### 5.5 The naming hazard this arbitration creates

A source repository often uses names that do not mean the same thing as here. That is how a reused block can invert a
semantics **without breaking any test**.

The clearest example: in the source repository, `known_at` designates **our** ingestion date. In this contract,
`KNOWN_AT` designates **publication in the source**. Taking the name as is would put `INGESTED_AT` under the `KNOWN_AT`
label — a silent contradiction that would invert point-in-time semantics without failing a single test.

**Arbitration: no name is taken when its meaning differs.** The correspondence is explicit:

| Source repository name | TORNE | Meaning |
|---|---|---|
| `event_time` | `VALID_TIME` | when the fact happened |
| `published_at` | `KNOWN_AT` | when the source made it public |
| `known_at` | `INGESTED_AT` | when TORNE acquired it |
| `usable_from(published_at, known_at)` | `usable_at(KNOWN_AT, INGESTED_AT)` | derived function |

A reuse without a correspondence table is not a reuse: it is a copy.

### 5.6 A deliberate divergence

The source repository sets `usable_from(published_at=None, known_at=…) = known_at`, thus replacing an unknown
publication with the ingestion date. TORNE does not take that fallback (§3.9): it carries the "unknown" or "bounded"
publication state, and refuses point-in-time admission without evidence or a conservative bound.

The divergence is **deliberate**, from a retained block. It is justified by a programme invariant ("never fill missing
metadata with an assumption") and by `docs/RESEARCH_AND_VALIDATION.md` §4 ("on evidence or a conservative bound"). It
must stay visible in the code.

### 5.7 "Local first, copy after"

The local store is the truth; a remote copy is a copy. A remote storage failure delays the copy, it loses nothing.
Three rules follow:

1. **Local first, copy after** — the copy is never upstream of the local truth.
2. **Integrity by digest, never by decoding** — one checks the digest matches, not that the content "reads well".
3. **Consistent index snapshot** — the copy carries a consistent index, never a partial view.

### 5.8 A rule is not a guarantee until it is tooled

Three statuses, not to be confused:

| Status | What it commits |
|---|---|
| **written** | it commits only its author |
| **tooled** | it is verified by execution — a test checks it |
| **documented** | it commits only its reader |

A rule that is only **written** is not a guarantee. Each invariant of §4 is phrased as a question a test must answer
yes or no; as long as the test does not exist, the invariant is **written**, not **tooled**.

## 6. What depends on a particular source

The programme forbids imposing a generic storage or connector design before "the sources actually available are known,
qualified and dated". This contract therefore stops before anything that depends on a particular source.

### 6.1 What is contractual, and depends on no source

- The five objects: responsibilities, invariants, what they do not guarantee, relations (§1–§2).
- The three time dimensions, their order, and the fact that `usable_at` is derived (§3.1–§3.2).
- The usability rule `max(KNOWN_AT, INGESTED_AT)` and its three consequences (§3.2).
- The treatment of unknown publication: *established / bounded / unknown* states and the admission rule (§3.9), and
  the four source classes (§3.11).
- The revision rule: new version, history not rewritten, invisibility before the date (§3.6).
- The treatment of provisional statuses (§3.7) and absences, with `missing_reason` (§3.8).
- Raw evidence preservation and the ban on silent overwriting (§2.2, INV-01 to INV-06).
- The four-element minimal lineage (INV-27) and the rebuildability of derived data (INV-28).
- The anti-leakage synthetic store as an invariant (INV-32 to INV-34).
- The "one of each" arbitrations of §5.
- Acquisition conformity: semantic conformity distinct from data presence, exhaustiveness qualified per source,
  adapter errors turned into outcomes (INV-37 to INV-40).
- Secrets and credentials: by reference only, never across an origin (INV-41, INV-42).
- Global randomness never touched; sampling components deterministic for a fixed seed (INV-35, INV-36).
- Nature of a result and operational status are distinct (INV-43).
- Real-time estimates separated from reconstructions using the future, and estimated parameters kept (INV-44, INV-45).

### 6.2 What waits for source qualification

Each row says **what is needed** to decide.

| Deferred point | What is needed |
|---|---|
| **Establishing `KNOWN_AT` per source**: where does the publication date come from (HTTP header, document metadata, payload field, file date)? | The real response content and metadata, for each retained source — that is source qualification (`docs/SOURCES.md`). |
| **The conservative bound when publication is unknown**: which bound is defensible per source? | The observed publication granularity and update frequency of the source. |
| **Granularity retained per source**, and the aggregation rule. | The real parameters of each dataset. |
| **Civil date convention per source**: does a week "ending Saturday" end in the issuer's local time or in UTC? | The issuer's declared time zone and the cut-off time of its publication cycle. |
| **Quality status mapping**: what do "provisional", "estimated", "approved" of each source map to in the closed vocabulary of §3.7? | Each source's quality documentation, not its field name. |
| **`missing_reason` values per source**: "not measured", "not published", "series stopped", "instrument failure", "out of domain"? | An inventory of the absence reasons actually met in each source's data. |
| **Revision policy per source**: does a revision create a new observation version or only a new file version? Does the source date its revisions? | Documentation and empirical observation of each source's revision behaviour. |
| **Unit registry**: which storage unit for discharge, level, tonnage? Which vertical datum? | Open. The spatial vocabulary now exists (`src/torne/contracts/spatial.py`) and keeps coordinates in the source's reference system without projection; no unit registry exists, and units are kept in the source's terms. |
| **Shape of the "raw" per source**: a file, a JSON response, a table row? Is there a stable acquisition unit? | Direct observation of real responses. |
| **Computing `usable_at` per source** | The classification rule is given (§3.11). Its **per-source instantiation** — effective class, bounds, cycles — is source qualification. |

> **What still blocks.** The **rule** for computing `usable_at` is written (§3.11). What remains is its **per-source
> instantiation**, which cannot be done by assumption: it requires having **queried** each source and observed what
> it exposes.

---

## 7. What could not be decided

Three points are neither a design error nor an oversight: they cannot be decided before the data are known.

1. **Can the revision history be rebuilt?** It depends entirely on the source: a source that dates its revisions
   allows it; one that does not, does not, and the contract can only record the absence. **It is not a design
   question.**
2. **The common granularity between sources.** Aligning a weekly flow on an hourly flow requires choosing an
   aggregation rule and an attachment convention. The aggregation rule is contractual (§3.3); the **choice** of common
   granularity is not. BASIN-001 is the first mission that must make this choice.
3. **The quality of the operational point of view.** "How far can TORNE claim what it knew *then*" depends on the real
   collection frequency, an operational fact, not a design one.

To which a point of **method** is added: the contract says what must be verifiable, not how to test it. An
anti-leakage test needs a simulated-date harness; its form is the synthetic store (§4.6).

---

## The ten decisions this document takes

1. **Five objects, five responsibilities** — five questions each object answers alone (§1.1); relations are a data
   lineage, not a mandatory pipeline (§1.3).
2. **Three stored time dimensions, nothing more.** Availability time is a **derived function** (`usable_at`), use time
   a **query parameter** (`asof`), the issuer's declared date **source metadata** (§3.1).
3. **No name is taken when its meaning differs** (§5.5).
4. **`usable_at = max(KNOWN_AT, INGESTED_AT)`, never stored**, with ingestion before publication flagged as doubtful
   and the natural order `VALID_TIME ≤ KNOWN_AT ≤ INGESTED_AT` (§3.2).
5. **An unknown publication is not replaced by the ingestion date.** Three states and an admission rule; "unknown"
   **excludes** the observation from point-in-time reconstruction (§3.9), a deliberate divergence from the source
   repository (§5.6).
6. **Revision does not rewrite history** (§3.6, INV-12, INV-13).
7. **Absent ≠ zero, and absence has three forms**; an absence is never filled by an assumption (§3.8).
8. **Raw data is never silently overwritten** (§2.2, INV-01 to INV-06).
9. **The four-element minimal lineage and the synthetic store are invariants, not good practices** (§4.4, §4.5).
10. **One responsibility, one implementation**, every reused block classified before it enters (§5.1, §5.3); "raw =
    truth, derived = rebuildable" and "local first, copy after" are retained (§5.7).

---

## The five questions that remain open

1. **How is `KNOWN_AT` established for each retained source?** Closed source by source by qualification
   (`docs/SOURCES.md`).
2. **Which conservative bound is defensible when publication is unknown** — one per source, from its publication
   cycle, or a uniform one? The fallback `usable_at = INGESTED_AT` **is not reopened**.
3. **Which common granularity, and which attachment rule between sources of different frequencies?**
4. **Which unit registry** — keep source units or convert — and which vertical datum for hydrological quantities?
5. **Do source quality statuses map cleanly onto the closed vocabulary of §3.7**, and which `missing_reason` values are
   actually met?

*The points of §6 are explicitly referred to it, and the five questions above cannot be decided before the sources are
qualified.*
