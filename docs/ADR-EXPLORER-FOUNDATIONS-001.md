# ADR — EXPLORER-FOUNDATIONS-001: the frontend and the API it serves

**Status: accepted.** Date: 2026-11-01. Mission: EXPLORER-FOUNDATIONS-001.

## Context

TORNE Explorer was a single `app.js` of 529 lines that built HTML strings, rendered a map with
Leaflet, and fetched its data from a CDN at runtime. The API behind it was one FastAPI module
whose responses were `dict[str, Any]`, with no versioning and no declared response model.

The mission had to establish foundations that the next domains — Water Intelligence, and later
Market and Opportunity Intelligence — could be built on without rewriting the interface, the
chart components or the backend. The architecture forbids a general-purpose UI library, a second
charting library, a microfrontend architecture, a global store, Tailwind, and any 3D dependency.

## Decisions

### 1. React 19 + TypeScript strict + Vite 8, in a `frontend/` root of its own

A compiled static application, served by FastAPI in production and proxied to it in development.

*Why.* The explorer was going to grow into several applications over one catalogue. Components
that receive typed data through their props, and that know nothing about HTTP, are reusable
across applications; a module that writes HTML strings is not.

*TypeScript 6.0.3, not 7.0.2.* TypeScript 7 is the native port and is the current `latest`, but
`typescript-eslint@8.72.1` declares `typescript@>=4.8.4 <6.1.0`. Adopting 7.0.2 would mean
either dropping the type-aware lint rules or running a linter that cannot load. 6.0.3 is the
current stable line the whole toolchain supports. The decision is recorded here so that the
upgrade is a deliberate one, made when the ecosystem moves.

*Licences.* React, React DOM, React Router, Vite, Vitest, Testing Library, jsdom, ESLint and
Leaflet are MIT; TypeScript and Apache ECharts are Apache-2.0; Leaflet is BSD-2-Clause.
`world-atlas` and `topojson-client` are ISC.

### 2. Apache ECharts 6, imported piecemeal

`echarts/core` plus the charts and components actually used, split into its own chunk. A page
that shows no chart does not download the chart library.

*Why.* The charts have to do things a generic line chart does not: keep the holes in a series
open, draw an envelope only when an interval exists, place irregular levels on a value axis, and
distinguish an observation from a forecast by dash pattern as well as by colour. Those are
options on a general-purpose engine, not a component library.

*Rejected.* Chart.js (no equivalent support for the envelopes and the custom axes these charts
need), D3 (would mean writing the axes, the scales and the zoom by hand), and a second charting
library for the map (the map is Leaflet, and it stays Leaflet).

### 3. One design-token file, three colour registers, no hard-coded colour

`tokens.css` defines the surfaces, the typography, the spacing, the states, the semantic colours
and the palettes. Light and dark are expressed with `light-dark()` against a single
`color-scheme: light dark`, so every token has exactly one definition.

Three registers are kept strictly apart, and the distinction is enforced by the naming:
`--science-status-*` is the ordinal ramp of what a mission produced, `--series-*` is the
categorical Okabe–Ito palette for data, and `--accent-*` is decorative and interactive only.
A series colour is never a status colour, and an accent is never a data colour.

Colour is never the only channel: a series also carries a symbol, a forecast also carries a dash
pattern, and a status also carries its name.

**The legend's swatch is derived from the mark the chart draws.** A legend that advertises a shape
the chart does not draw is a legend that lies, and a kind carried by its colour alone is not
carried at all. The two are therefore one value: a kind names a mark, the mark names a swatch,
and the chart draws the mark. A period that does not exist is drawn as an empty outline, because
an absence is not a pale period.
### 4. Leaflet is kept, and the map draws no tiles

The map shows TORNE's own layers on a plain background. An external tile service would make the
application depend on a third party at runtime and would draw a world the explorer knows nothing
about. The boundaries are prepared at build time from `world-atlas` and served from the
application's own origin: 365 kB, against the 739 kB the CDN used to serve.

### 5. The API is versioned now: `/api/v1` is canonical, `/api` still answers

`/api/v1` is the only prefix the OpenAPI document describes. `/api` answers the same questions
and marks its answers `Deprecation: true`, with a `Link` header pointing at the successor. The
migration is therefore something a consumer does, not something it suffers.

*Why now.* Versioning after the consumers have multiplied means changing everyone's URL at once.

**The removal of the legacy prefix has a published rule.** It goes away in one announced step,
once the first application published outside this repository consumes `/api/v1`, and never as a
side effect of another change. The rule is stated in the OpenAPI description — where a consumer
reads it — and a test refuses the application if it stops being published: a deprecation without
a published rule is a side effect waiting to happen.

### 6. Every response has a Pydantic model; every error has the same shape

A route without a `response_model` leaves the OpenAPI document a guess, so a test refuses the
application if one is missing. Errors carry `detail` — the field FastAPI has always returned, so
an existing consumer keeps working — and `error`, a stable machine-readable code.

### 7. The frontend keeps the API's own field names

The TypeScript types mirror the Pydantic schemas field for field, in `snake_case`. A camelCase
mirror would be a second contract, free to drift from the first, and a mapper is exactly where a
`null` — an unknown, which the API takes care to preserve — could quietly become a zero.

### 8. The visualization contracts mirror the engine's vocabularies, and only the representation

`PointValidity`, `MissingReason`, `QualityStatus` and `PublicationState` carry the engine's own
words. The frontend defines the contract of **representation** of what the API exposes; it does
not define physics, and it depends on no Python class.

### 9. One system, two skins

The Explorer is read in two conditions: at a console, where the reader is looking at an instrument,
and at a desk, where the reader is looking at a report. Rather than choose, the system carries
both: a dark **cockpit** skin and a light **journal** skin, over one grammar of components.

A skin is a set of values, never a fork of the code. Every colour token holds both values through
`light-dark()`, and a component reads the token; it never chooses. A stylesheet that names a
colour has left the system, and that is the rule a reviewer can check.

The two skins are not one derivation of the other. The cockpit separates with hairlines and
lightness, the journal with hairlines and soft elevation; the cockpit's accent is a luminous
ember, the journal's a deep one. What they *share* is the semantics: the categorical register
keeps the same eight Okabe–Ito hues in both, the dark skin lifting their lightness rather than
re-choosing them, so a chart means the same thing whichever skin the reader is in.

*Why not one skin.* A single skin forces a compromise — a light skin that is too dark to read a
figure on a bright room, or a dark skin that is too dark to read in a lit room — and the reader
pays for the compromise.

*Why not two systems.* Two systems is twice the work and two chances to drift apart, and the
second skin would arrive with the wrong semantics baked in.

### 10. The canvas is part of the system

A canvas has no stylesheets: the grid, the axes, the ticks, the tooltip and the zoom track are
options in concrete values, for every chart. Left to itself each chart describes its own
furniture, and four charts end up looking like four applications.

`src/components/visualization/chartCraft.ts` is that furniture, built from the chart tokens — one
grid, one time axis, one value axis, one category axis, one tooltip, one legend, one zoom. The
charts read the same tokens the DOM reads, and **the figures are set in the mono face**, because
an instant, a measurement and an identifier are read in columns.

**The unit is written once, on a label plate.** The plate sits beside the title of the figure, in
the place where the reader looks for it. When the series disagree on their unit, the plate says
*unit not established* and the axis says nothing — an axis labelled "unit not established" states
nothing a reader can use, and it collides with the legend that explains the axis.

**The selection on a map is an outline, never a change of fill.** The fill of a country is what
the choropleth encodes — the highest status its own missions earned — and that does not change
because the reader is looking at it. A station carries no status, so a station takes the fill.
This is the same rule the rest of the system obeys, applied to the drawing code rather than
described in a document.

## Consequences

- The Python package ships the compiled application: the wheel is self-contained, and
  `src/torne/explorer/static/` is a build artefact rather than hand-written source. The ignore
  rules re-include it explicitly: the repository's `data/` rule matches any directory of that
  name at any depth, and the compiled tree holds one.
- The frontend has its own toolchain. `npm run build` type-checks, lints and builds; `npm test`
  runs the unit suite; `npm run test:e2e` runs the browser suite against the application FastAPI
  actually serves.
- The components are reusable by the next applications without touching the API: a chart receives
  typed data through its props and never calls the API itself.
- The Explorer keeps working while the new applications arrive: the map, the catalogue and the
  provenance are unchanged in meaning.

## What this does not decide

The deferred charts — heatmaps, scalar field maps, scatter plots, distributions, correlation
matrices, network diagrams, calibration plots — stay deferred. A component is written when its
contract and its use are clear.

MapLibre, Cesium and any 3D globe stay out. The financial branch stays closed.

## Verification

- `npx tsc --noEmit`, `npx eslint .`, `npx vitest run`, `npx playwright test` in `frontend/`.
  The browser journeys run on Chromium, Firefox and WebKit.
- `uv run pytest` in the repository root: the explorer suite, plus a suite that checks the
  versioned API, the error shape, the declared response models, and that no scientific module
  imports FastAPI.
