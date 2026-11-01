# ADR — KNOWLEDGE-PUBLICATION-001: the first published product, and the branch it opens

## Context

`docs/CORE_CONTRACTS.md` has defined the **Knowledge Product** since the beginning: an identified, versioned,
reusable result, carrying its lineage, the quality status of everything it consumes, its domain of validity and a
qualified uncertainty. The Explorer was built to serve that contract.

It could not serve it. `knowledge.record.ExecutionRecord` lived in memory, and the mission scripts wrote their
evidence to temporary directories. **The Explorer therefore listed no knowledge product, and said so** — which was
honest, and was also the end of the road: a catalogue that can only describe runs in memory cannot show a result, and
a reader who cannot see a result cannot judge it.

Mission LNG-002 (European gas supply) produced a product. The production output exists, in French, in
`data/resource-004/` — which is not versioned, because it is a production output and not a source. It was a
publication problem, not a contract problem.

This ADR records the decisions that turned that production output into something the Explorer can read, and the
branch that the reader reaches through.

## Decisions

### 1. The contract was not the missing piece; the persistence was

`contracts/knowledge.py` already defined `KnowledgeProduct` completely, with its own checks: a non-empty lineage, a
status for every cited input, an input status for every lineage entry, a UTC instant. Nothing was rewritten.

What was missing was a **place to put a product**. The store (`knowledge/store.py`) is that place, and it is
deliberately small:

- one JSON file per version, carrying the product's own serialisation, and beside it the payload the product points
  at;
- the digest of the payload is written **into** the record, so a reader can tell whether the payload it reads is the
  one that was published;
- the store computes nothing and calls no provider. It reads and writes files. A product that is not on disk is not a
  product.

The store is **application-independent**. It knows nothing about gas, nothing about hydrology and nothing about the
Explorer: it holds products, and it holds them the way `KnowledgeProduct` says they must be held. The gas-specific
half lives in the API's schemas, which say so in their own docstring: the indicators are typed for one product, the
first, and they do not pretend to be a registry.

### 2. A published product is not rewritten — its description included

INV-31 says a published product is not rewritten, and a correction is a new version. The store enforces it on the
**payload**: writing a version whose payload differs raises `RecordExists`.

It was enforcing it only on the payload, and that was a hole. A publisher who changed what the product *says* — its
domain of validity, a bound's statement, the list of the countries that published nothing — while the payload stayed
identical would get a silent success and an unchanged file on disk. The publication would appear to have happened
and would not have happened at all.

The store now compares the **record** as well, and refuses it the same way. Publishing the same product again, with
the same payload and the same record, is still a no-op: the publication is re-runnable, which is what makes it
trustworthy.

### 3. The publication is a script, and the script verifies what it published

`scripts/publish_gas_supply.py` is the boundary between the two worlds. It reads the production output — French
column names, French units, French prose — and writes the **published contract**: English column names, English
units, English prose, and the numbers unchanged.

Translation is the work of publication. A number is not translated; a name is. The published column names
(`stock_gwh`, `derived_entry_gwh`, `computed_coverage_days`) are the contract, and the production names
(`stock_gwh`, `entree_derivee_gwh`, `couverture_calculee_jours`) are the accident of one production run.

The script has two modes, and they are separate:

- without an argument it **publishes**;
- with `--check` it **verifies** what is committed and writes nothing.

The check is not a smoke test: it recomputes the digest of every production file the record cites, counts the states
the payload holds, reconciles the declared window with the payload's own days, checks that the installations the
record declares without data are absent from the payload, and re-derives the figures of the confrontation from the
published rows. **A product whose check fails is not published.** The committed record and the script that wrote it
agree, or the repository says so.

### 4. The product declares its own absences

The storage layer answers for **30** countries. **19** published usable states. The other **11** published nothing.

The record says so twice: in its `domain_of_validity` ("the 30 countries the platform answered for — 19 of them
published usable states"), and — because prose is not a contract — in a field,
`indicators.storage.countries_without_published_state`, that names the eleven.

This is the same rule the terminal layer already follows with `installations_without_data`. It is stated here because
it is the rule that is easiest to break by accident: a reader who sees 19 countries on a map of 30 would conclude
that eleven countries have no storage, or that the product is incomplete. The product must say **which** is true,
and it must say it in a field the API can serve.

The consequence runs through the whole chain: the API serves 19 states and a declared list of 11; the frontend shows
19 and says "no state published" for the eleven. **The absence is visible at every step, and it is never a zero.**

The same rule governs the gaps inside a series. Two installations do not publish every day of the window, and the
days they do publish are complete. The derived entry — the difference between two stocks and the withdrawal of the
day — needs the previous day: it is absent on the first day of a series, and it is absent on the day after a gap,
because the day before that one is unknown. An absence stays an absence all the way down, and the publication says
so rather than interpolating.

### 5. The API serves the product; it never recomputes it

`/api/v1/products`, `/api/v1/products/{id}`, `/api/v1/products/{id}/states?layer=&entity=` and
`/api/v1/products/{id}/confrontation` serve what the record carries.

- A product that was never published is a **404**, not an empty product. An absent product is an absence.
- A quantity the payload does not carry is **null**, not a zero. The first day of a series has no derived entry
  because it has no previous day, and the API says so with a null.
- The service reads; it never recomputes, rounds or reinterprets. The numbers served are the numbers the published
  record carries, and the service's own test asserts that, against the record read from disk.

The states route has one rule worth stating: **without an entity, it serves the last published state of every
entity** — what a map draws. **With an entity, it serves the whole series** — what a chart draws. One route, two
questions, and the difference is a parameter.

### 6. The branches are read from the manifest, not written in the bar

The Explorer had two spaces in its top bar: "World Intelligence", and a "Market Intelligence" that was hardcoded,
disabled, and explained by a `title` attribute. That was a promise about a future branch, written in the component
that displays the branches.

The manifest now carries **`branches`**: each with its id, its title, whether it is **open**, **why** it is open or
closed, and the domains, missions and products it stands on.

- `supply` is **open**: the physical engine is validated — the European gas supply is published as a knowledge
  product, and confronted with an independent source on the seven Spanish terminals.
- `market` is **closed**, and now says why in a sentence a reader can see: the supply side is validated, but no
  price, no margin and no counterparty is sourced. Turning physical intelligence into a financial decision has
  nothing to read yet.

The bar reads the list. An open branch is a link; a closed branch says that it is closed and carries the reason.
**A branch title is written once, in the manifest**, and the interface is not allowed to hold a second opinion
about which branches exist.

### 7. The branch reads the product; it does not read the catalogue

A branch is not a filter on the catalogue. It is a reading of a **published product**, and the product is what the
branch serves: its identity, its two layers, its bounds, its confrontation and its provenance.

This is the difference between a catalogue and an intelligence. The catalogue says what the platform has touched;
the product says what it has established, with the evidence attached. A branch that filtered the catalogue would
show missions; a branch that reads a product shows a result — and the result can be wrong, bounded, or partial, and
says so.

## Consequences

- **The Explorer now serves a product.** `/api/v1/products` lists one, and the Supply Intelligence branch reads it.
- **The first product is a gas product, and the API says so.** The indicators are typed for it. The store, the
  record and the list of products are generic; the typed half is the application, and it says that it is the first
  application rather than pretending to be a framework.
- **The production output stays out of the repository.** `data/resource-004/` is not versioned, and the published
  record carries the digest of each file it was built from — so a reader can tell that the production moved, and the
  `--check` says so instead of the repository lying quietly.
- **A re-publication needs a new version.** When the production moves, the product moves with it, and the old
  version stays consultable.
- **The manifest's "results" section now separates what is persisted from what only ran.** A run that produced a
  product in memory is still listed apart from a published record, and the gap the manifest names is the gap that
  remains, not a fixed sentence.

## What this does not decide

- **The Market Intelligence branch stays closed.** Nothing here prices anything.
- **The gas sources are still unqualified.** No gas source is registered in `SOURCES`, because the qualification
  belongs to the RESOURCE workstream. The record's `source_ids` is therefore empty, and the absence is declared in
  the manifest's `planned` list rather than hidden.
- **The store is not a registry.** It holds products; it does not catalogue them, and it does not know what a
  mission is.

## Verification

- `python -m pytest` — the full suite, including `tests/test_knowledge_store.py`,
  `tests/test_gas_supply_record.py` and `tests/test_explorer_api_products.py`.
- `python scripts/publish_gas_supply.py --check` — the published record agrees with what is committed.
- `python scripts/dump_openapi.py --check frontend/src/types/api/openapi.json` and
  `python scripts/generate_types.py --check` — the served contract is the committed contract.
- `npx tsc --noEmit`, `npx eslint .`, `npx vitest run`, `npx playwright test` in `frontend/`.
