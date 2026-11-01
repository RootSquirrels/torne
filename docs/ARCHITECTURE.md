# TORNE — Architecture

**Boundaries, responsibilities and layers**
**Status: responsibility view.** This document does not describe an implementation: it fixes **where each
responsibility goes**, not how it is delivered. The code applies it; it is not its source. When the two diverge,
the document is wrong, and it is corrected.

## 1. The mental model

```text
SOURCES
   ↓
MODELS
   ↓
KNOWLEDGE PRODUCTS
   ↓
APPLICATIONS

PROVENANCE · TEMPORALITY · UNCERTAINTY · VALIDATION   (cross-cutting)
```

Four concepts are enough. Physical, operational, economic and financial models are **specialised, composable
model families**, not mandatory successive stages: there is no universal chain, and a model can consume sources
directly or the products of other models.

The boundaries are **logical**. They imply no microservices, no separate deployment, no event bus, and no strictly
linear execution.

### 1.1 Three levels, separated by explicit contracts

Across the four boundaries, the repository distinguishes three **levels** of responsibility, which never mix in
one module:

| Level | What it contains | What it does not contain |
|---|---|---|
| **Cross-cutting socle** | acquisition, transport, evidence storage, data contracts, execution, fingerprinting | no domain knowledge: no discharge, no water level, no time series semantics |
| **Semantic layer** | what gives domain meaning to socle objects: reading a source into observations, derived quantities | no direct network or raw-store access |
| **Scientific layer** | methods: regression, breaks, power, state filtering, comparison to a reference | no writes, no network access |

The separation is not cosmetic: it lets a method be added without touching the socle, and a source be added
without rewriting a method. A source adapter knows nothing of the domain — it builds a URL and says how the source
is walked; a model knows nothing of the network.

### 1.2 Domains are modalities, not platforms

`hydrology/`, `atmosphere/` and `eo/` are semantic layers for **modalities of observation of one physical world**.
They do not carry their own contracts, evaluation, or knowledge records: those belong to the socle and are shared.
A reconstruction that combines modalities — the purpose of TORNE — lives in the scientific layer and consumes the
observations of several semantic layers; it never reaches into an adapter.

## 2. Boundary 1 — Sources

**Question:** where does the information come from, and under what conditions was it available?

**Responsibility:** identify the producer of a piece of information, acquire the raw content, keep it, date it,
version it, normalise it, and qualify its availability. A source is a producer or holder of information; an
observation is a datum about a state or an event of the world.

**What this boundary guarantees:**

- the exact version of the data is identifiable and reproducible;
- validity time, publication time and availability time are distinguished;
- identity, units and spatial references are carried by the data, not by the code's memory;
- a revision is visible and is never presented as if it had been available at the time.

**What it does not do:** it infers nothing. A source does not produce knowledge; it provides the material knowledge
is derived from.

**The four rules acquisition must hold.** This is where error is easiest to commit and hardest to see: one can
believe one obtained what was asked without having obtained it. Each rule is a verifiable invariant
(`docs/CORE_CONTRACTS.md` §4.8 and §4.9):

- **Raw data is not semantic conformity.** An adapter verifies, on the rows actually received, that the requested
  identifiers are the ones that come back; it does not assume the provider obeyed. **A filter echoed in the URL is
  not evidence of filtering**: a provider can accept a filter, echo it in its links, and ignore it in the
  population it returns.
- **The predicate belongs to the source; the socle only orchestrates.** The socle knows neither station identifiers,
  nor units, nor domain rules: it records the verdict, it does not decide it. **Transferability predicates**
  (`docs/RESEARCH_AND_VALIDATION.md` §12) are not concerned here: they belong to the validation of claims, not to
  acquisition.
- **Exhaustiveness is qualified per source.** A successful HTTP response does not prove the provider returned every
  expected observation: either the source says so or it does not, and the walk may be truncated by our own budget.
- **An adapter error is a result, not an exception.** A malformed response produces a structured outcome —
  `failed` or `partial` — and the attempt is recorded like any other.
- **A secret only travels by reference.** What is recorded — journal, manifest, fingerprint — carries a reference,
  never the value; and a credential does not cross a redirect that changes host, port or scheme.

**Two axes, and one gate.** Conformity has its **own** axis and its **own** verdict; the acquisition status only
speaks of acquisition — did the response arrive, was the page kept? — and says nothing about whether the response
answers the question asked. A source that returns another station's rows **creates no observation**: the gate is
`exploitable`, and it alone decides use. It is not an acquisition failure: the response did arrive, was kept and
fingerprinted — a non-conforming response is evidence, and all the more useful for being known not to fit. A
verdict without a reason is not accepted.

**Note:** the temporal rules of the sealed protocol of the former electricity project are out of scope and not
taken over. TORNE defines its own temporal conventions, built on the canonical distinction between validity,
publication, receipt, availability and use times (`docs/CORE_CONTRACTS.md` §3.1).

## 3. Boundary 2 — Models

**Question:** which scientific or operational question are we addressing?

**Responsibility:** transform inputs into results according to an explicit method and explicit assumptions. A model
has a precise question, a domain, inputs, an output, assumptions and declared limits.

**What this boundary guarantees:**

- a result always states what it is: reconstructed state, estimate, forecast, simulation, derived variable,
  constraint, mechanism or economic consequence;
- assumptions are written, not implicit;
- the domain of validity is stated;
- uncertainty is qualified according to what is actually known.

**What it does not do:** it does not turn an estimate into an observation, nor a simulation into a fact. A model is
not an engine because it has several steps; an engine is a functional grouping, and its existence must be justified
by a distinct responsibility and a demonstrated operational reason.

## 4. Boundary 3 — Knowledge products

**Question:** which reusable result do we publish?

**Responsibility:** produce versioned, documented results meant to be consumed by an application or audited. A
product is a state, an estimate, a forecast, a simulation, a constraint, a mechanism or an economic consequence.

**What this boundary guarantees:**

- a version, a timestamp and a provenance;
- an uncertainty and a domain of validity;
- the link to the sources, transformations, models and parameters that produced it;
- an explicit validity status: usable, degraded, withdrawn, or inconclusive.

**What it does not do:** it is not a registry. A product is published only if it must be reused, audited or
consumed independently; internal intermediates stay internal. No index, catalogue or registry is created in the
repository until a real need justifies it.

## 5. Boundary 4 — Applications

**Question:** which decision or understanding does this result enable?

**Responsibility:** consume knowledge products to produce an understanding, an alert, a map, an exposure analysis or
a research hypothesis. Financial intelligence is one application among others, not the owner of the socle.

**What this boundary guarantees:**

- the application does not modify the products it consumes;
- the declared use: which result, for which decision, under which conditions;
- the failure of an application does not call valid products into question.

**What it does not do:** it does not decide the validity of a model. An application that succeeds does not validate
the upstream models retroactively.

**TORNE Explorer** (`src/torne/explorer/`) is the first application. It is read-only and bound by three rules: it
performs no scientific computation and never calls a data provider; it only shows metadata and results the repository
has actually established (a mission's status is earned by its evidence, and `knowledge` requires a persisted record);
and it never shapes the engines to its display needs. Its web stack (FastAPI, uvicorn) is an optional extra that no
other package imports.

**The financial branch is not open.** The "world-to-market" branch — turning physical-world intelligence into a financial
decision — is **deferred** until the physical intelligence engine is mature. The deferral is deliberate and follows
from the rule above: a financial application that succeeds does not validate the physical models upstream, and has
nothing to say about their correctness. It will open when the knowledge products it consumes are themselves
validated.

## 6. Cross-cutting concerns

The following four concerns are not a fifth boundary nor a layer: they apply to every element of the diagram and
copy neither data nor functions.

### 6.1 Provenance

Every conclusion traces back to the sources, versions, transformations, models and parameters that produced it. A
result without provenance is not publishable: it is neither reproducible, nor auditable, nor reusable.

### 6.2 Temporality

A datum carries several distinct, non-interchangeable instants: the one the fact refers to, the one the issuer
declares, the one at which the version was accessible, the one it was received, the one it becomes usable, and the
one it is used. A revised version is not presented as available at the time without evidence. Absent data carries
the reason for its absence; it never carries zero in place of absence.

### 6.3 Uncertainty

Uncertainty is described according to what is known: data, parameters, model structure, initial conditions,
numerical approximation, scenario. Its form fits what is actually known: interval, distribution, scenarios, bound,
sensitivity, or qualitative conclusion. A sophisticated distribution is not required if the data do not justify it.
The unknown is never replaced by zero, and dependent outputs are not counted as independent confirmations.

### 6.4 Validation

Validation is chosen according to the claim tested, never applied uniformly. It is described in
`docs/RESEARCH_AND_VALIDATION.md`. Physical, economic and financial validation stay distinct, and a judge that
depends on another is not an independent confirmation.

## 7. Responsibility boundaries

| Boundary | Guarantees | Does not |
|---|---|---|
| Sources | Version, date, quality, provenance of the information | Infer anything, produce knowledge |
| Models | Method, assumptions, limits, nature and uncertainty of the result | Turn an estimate into an observation |
| Knowledge products | Version, provenance, domain of validity, status | Act as a registry or catalogue what exists |
| Applications | Declared use and conditions of the decision | Validate upstream models |

Two cross-cutting non-duplication rules:

1. A cross-cutting layer copies neither the data nor the functions it governs.
2. A shared contract contains only the fields that are really common; domain detail stays in the domain.

## 8. What this architecture does not create

It proposes today no engine, no service, no registry, no bus, no graph, no plugin framework, no workflow system,
and no package directory meant to contain them. The boundaries are responsibilities for the code to fulfil, not
directories to create.

Further rules, which bind what the repository has accepted to contain:

- **One responsibility, one implementation.** The repository never hosts two building blocks with the same
  responsibility, and every block taken from a source repository is classified before it enters — REUSE, ADAPT,
  REIMPLEMENT or REJECT — with its origin declared at the top of the module (`docs/CORE_CONTRACTS.md` §5). The one
  known exception, two day-of-year climatologies, is recorded in `docs/PROGRAMME.md` §6.
- **No runtime dependency without a real import.** A dependency that is never imported is not a dependency: it
  appears neither in `pyproject.toml` nor in the lock file.
- **No generic model replaced by its state of the art.** A model enters because the available data and the quantity
  to reconstruct call for it, not because it was rated elsewhere.
- **No model library for a domain before that domain has a first problem.**
- **No global Bayesian framework, no validation, simulation or selection engine**: no demonstrated need justifies
  them (`docs/PROGRAMME.md` §8).

A new architecture proposal must answer four questions before it is accepted:

1. Which real problem or missing evidence justifies the change?
2. Why are the existing components not enough?
3. What is the smallest change that solves the problem?
4. How will we know it improved the system?

Without these answers, the proposal remains a hypothesis or is rejected.
